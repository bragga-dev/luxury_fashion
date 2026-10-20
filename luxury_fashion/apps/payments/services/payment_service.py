"""
Payment Service — orquestra a criação/consulta/estorno de cobranças na
Asaas e a aplicação do webhook. Fala com o AsaasClient; repositories só
persistem o que o service já decidiu.
"""
import hmac
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.core.exceptions import (
    AsaasAPIError,
    CpfOrCnpjRequired,
    InvalidWebhookToken,
    OrderAlreadyPaid,
    OrderNotFound,
    OrderNotPayable,
    PaymentNotFound,
    PaymentNotRefundable,
)
from luxury_fashion.apps.payments.integrations.asaas_client import AsaasClient
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.notifications.services.notification_service import notify_order_refunded
from luxury_fashion.apps.payments.tasks.order_notifications import queue_email, send_payment_refunded_email
from luxury_fashion.apps.payments.repositories.asaas_customer_repository import create_asaas_customer
from luxury_fashion.apps.payments.repositories.order_repository import (
    refunded_order,
)
from luxury_fashion.apps.payments.schemas.payment_schema import PaymentCreateIn, PaymentOut
from luxury_fashion.apps.payments.selectors.asaas_customer_selector import get_asaas_customer_by_client_id
from luxury_fashion.apps.payments.selectors.order_selector import get_order_by_id_and_user
from luxury_fashion.apps.payments.selectors.payment_selector import (
    get_open_payment_for_order,
    get_payment_by_asaas_id,
    get_payment_by_id,
    get_payment_by_id_and_user,
    get_payments_by_order,
)

from luxury_fashion.apps.payments.repositories.payment_repository import create_payment, update_payment
from luxury_fashion.apps.payments.services.order_service import confirm_order_payment, refund_order
from luxury_fashion.apps.payments.services.asaas_payment_mapper import (
    map_payment_creation_response,
    map_pix_qrcode_response,
    map_refund_response,
    map_webhook_payment_data,
)


_PAID_STATUSES = {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"}
_REFUND_STATUSES = {"REFUNDED"}
_REFUNDABLE_STATUSES = {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"}
_REFUNDABLE_BILLING_TYPES = {Payment.PaymentMode.PIX, Payment.PaymentMode.CREDIT_CARD}


def _get_or_create_asaas_customer(user_id: uuid.UUID, cpf_cnpj: str | None = None) -> str:
    client = get_client_by_user_id(user_id)

    existing = get_asaas_customer_by_client_id(client.client_id)
    if existing is not None:
        return existing.asaas_customer_id

    cpf = cpf_cnpj or client.cpf
    if not cpf:
        raise CpfOrCnpjRequired()

    asaas = AsaasClient()
    response = asaas.create_customer(
        name=client.get_full_name(),
        cpf_cnpj=cpf,
        email=client.user_id.email,
        external_reference=str(client.client_id),
    )
    create_asaas_customer(client, response["id"])
    return response["id"]


def create_payment_for_order(user_id: uuid.UUID, order_id: uuid.UUID, data: PaymentCreateIn) -> PaymentOut:
    # A cobrança é "reservada" (linha do Order travada + Payment criado
    # PENDING) dentro da transação, antes de chamar a Asaas — assim, um
    # duplo clique ou retry de rede concorrente encontra a reserva e cai
    # em OrderAlreadyPaid em vez de gerar uma segunda cobrança na Asaas.
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .filter(order_id=order_id, user_id=user_id)
            .first()
        )
        if order is None:
            raise OrderNotFound()

        if order.order_status != Order.StatusOrder.PENDING:
            raise OrderNotPayable()

        if get_open_payment_for_order(order.order_id) is not None:
            raise OrderAlreadyPaid()

        due_date = timezone.localdate() + timedelta(days=settings.ASAAS_PAYMENT_DUE_DAYS)

        payment = create_payment(
            order_id=order,
            billing_type=data.billing_type.value,
            value=order.total_geral,
            due_date=due_date,
            description=f"Pedido {order.code}",
            external_reference=str(order.order_id),
        )

    # A partir daqui o lock já foi liberado — o resto é I/O de rede com a
    # Asaas e não deve segurar a linha do Order.
    #
    # QUALQUER falha daqui até a criação da cobrança (CPF ausente, erro ao criar o
    # customer, erro ao criar a cobrança) precisa cancelar o Payment local reservado
    # acima — senão ele fica PENDING sem asaas_payment_id e get_open_payment_for_order
    # passa a barrar qualquer nova tentativa (OrderAlreadyPaid) num pedido que nunca
    # chegou a ter cobrança de verdade.
    asaas = AsaasClient()
    try:
        cpf_cnpj = data.credit_card_holder_info.cpf_cnpj if data.credit_card_holder_info else None
        customer_id = _get_or_create_asaas_customer(user_id, cpf_cnpj=cpf_cnpj)

        credit_card = data.credit_card.model_dump(by_alias=False) if data.credit_card else None
        credit_card_holder_info = (
            data.credit_card_holder_info.model_dump(by_alias=False) if data.credit_card_holder_info else None
        )

        response = asaas.create_payment(
            customer_id=customer_id,
            billing_type=data.billing_type.value,
            value=order.total_geral,
            due_date=due_date.isoformat(),
            description=payment.description,
            external_reference=payment.external_reference,
            credit_card=credit_card,
            credit_card_holder_info=credit_card_holder_info,
        )
    except Exception:
        update_payment(payment, status=Payment.PaymentStatus.CANCELLED)
        raise

    payment = update_payment(payment, **map_payment_creation_response(response))

    if data.billing_type.value == Payment.PaymentMode.PIX:
        # Nesse ponto a cobrança já existe de verdade na Asaas — se só a
        # consulta do QR Code falhar, não faz sentido derrubar a criação
        # inteira (o cliente ainda pode pagar pela invoice_url). Loga e
        # segue; os campos de Pix ficam vazios até uma nova sincronização.
        try:
            pix_data = asaas.get_pix_qrcode(payment.asaas_payment_id)
            payment = update_payment(payment, **map_pix_qrcode_response(pix_data))
        except AsaasAPIError:
            logger.exception(
                "Falha ao buscar QR Code Pix da cobrança %s (pagamento %s) — "
                "cobrança já criada na Asaas, seguindo sem o QR Code.",
                payment.asaas_payment_id, payment.payment_id,
            )

    from luxury_fashion.apps.payments.tasks.send_payment_request import send_payment_request

    transaction.on_commit(lambda: send_payment_request.delay(user_id, payment.payment_id))

    return PaymentOut.from_orm(payment)


def get_payment_for_client(user_id: uuid.UUID, payment_id: uuid.UUID) -> PaymentOut:
    payment = get_payment_by_id_and_user(payment_id=payment_id, user_id=user_id)
    if payment is None:
        raise PaymentNotFound()
    return PaymentOut.from_orm(payment)


def list_payments_for_order(user_id: uuid.UUID, order_id: uuid.UUID) -> list[PaymentOut]:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()
    return [PaymentOut.from_orm(p) for p in get_payments_by_order(order.order_id)]


def _do_refund(payment: Payment, value: Decimal | None, description: str | None) -> PaymentOut:
    if payment.status not in _REFUNDABLE_STATUSES or payment.billing_type not in _REFUNDABLE_BILLING_TYPES:
        raise PaymentNotRefundable()
    if value is not None and value > payment.value:
        raise PaymentNotRefundable("O valor do estorno não pode ser maior que o valor da cobrança.")

    asaas = AsaasClient()
    response = asaas.refund_payment(payment.asaas_payment_id, value=value, description=description)
    payment = update_payment(payment, **map_refund_response(response))
    queue_email(send_payment_refunded_email, payment.payment_id, "requested", str(value) if value is not None else None)
    return PaymentOut.from_orm(payment)


def refund_payment_as_admin(payment_id: uuid.UUID, value: Decimal | None, description: str | None) -> PaymentOut:
    """Estorno feito pelo admin: sem restrição de dono nem de etapa de envio."""
    payment = get_payment_by_id(payment_id=payment_id)
    if payment is None:
        raise PaymentNotFound()
    return _do_refund(payment, value, description)


def refund_payment(user_id: uuid.UUID, payment_id: uuid.UUID, value: Decimal | None, description: str | None) -> PaymentOut:
    payment = get_payment_by_id_and_user(payment_id=payment_id, user_id=user_id)
    if payment is None:
        raise PaymentNotFound()

    # O cliente só estorna sozinho enquanto o pedido ainda não foi pra separação/envio
    # (sem etiqueta). Depois disso o estorno passa pelo admin (troca/devolução).
    order = payment.order_id
    if order.frenet_order_id or order.shipping_status != Order.ShippingStatus.PENDING:
        raise PaymentNotRefundable(
            "Este pedido já foi enviado ou está em separação. Para estorno, entre em contato com o suporte."
        )

    return _do_refund(payment, value, description)


def _auto_refund_orphan_payment(payment: Payment, order: Order) -> None:
    logger.warning(
        "Pagamento %s recebido para pedido %s em status %s — estornando automaticamente.",
        payment.asaas_payment_id, order.code, order.order_status,
    )
    if payment.billing_type not in _REFUNDABLE_BILLING_TYPES:
        logger.error("Pagamento órfão %s (%s) não é estornável automaticamente — tratar manualmente.", payment.asaas_payment_id, payment.billing_type)
        return
    try:
        response = AsaasClient().refund_payment(
            payment.asaas_payment_id,
            description=f"Estorno automático: pedido {order.code} já estava {order.order_status}.",
        )
        update_payment(payment, **map_refund_response(response))
        queue_email(send_payment_refunded_email, payment.payment_id, "late_payment")
    except AsaasAPIError:
        logger.exception("Falha ao estornar pagamento órfão %s — tratar manualmente.", payment.asaas_payment_id)


def handle_asaas_webhook(token: str, event: str, payment_data: dict) -> None:
    if not settings.ASAAS_WEBHOOK_TOKEN or not hmac.compare_digest(token, settings.ASAAS_WEBHOOK_TOKEN):
        raise InvalidWebhookToken()

    asaas_payment_id = payment_data.get("id")
    if not asaas_payment_id:
        return

    payment = get_payment_by_asaas_id(asaas_payment_id)
    if payment is None:
        return

    status = payment_data.get("status")
    if not status:
        return
    payment = update_payment(payment, **map_webhook_payment_data(status, payment_data))

    order = payment.order_id
    if status in _PAID_STATUSES and order.order_status != Order.StatusOrder.COMPLETED:
        # É aqui que o estoque é debitado. False = pagamento não aceito (pedido já cancelado/
        # expirado, ou faltou estoque): estorna automaticamente e responde 200 pra Asaas
        # (antes isso virava 500 e o webhook era reenviado pra sempre).
        if not confirm_order_payment(order.order_id):
            order.refresh_from_db()
            _auto_refund_orphan_payment(payment, order)
    elif status in _REFUND_STATUSES and order.order_status != Order.StatusOrder.REFUNDED:
        if refund_order(order.order_id):
            notify_order_refunded(order.order_id)
        else:
            # Estorno de pagamento que nunca concluiu o pedido (ex.: pago depois de cancelado/expirado, ou
            # sem estoque): o pedido continua CANCELLED — não há transição nem "pedido reembolsado" a avisar.
            logger.info("Estorno %s recebido; pedido %s segue %s (sem transição).", asaas_payment_id, order.code, order.order_status)