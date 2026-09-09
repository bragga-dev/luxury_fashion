"""
Payment Service — orquestra a criação/consulta/estorno de cobranças na
Asaas e a aplicação do webhook. Fala com o AsaasClient; repositories só
persistem o que o service já decidiu.
"""
import hmac
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.core.exceptions import (
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
from luxury_fashion.apps.payments.repositories.asaas_customer_repository import create_asaas_customer
from luxury_fashion.apps.payments.repositories.order_repository import (
    refunded_order,
    completed_order,
)
from luxury_fashion.apps.payments.schemas.payment_schema import PaymentCreateIn, PaymentOut
from luxury_fashion.apps.payments.selectors.asaas_customer_selector import get_asaas_customer_by_client_id
from luxury_fashion.apps.payments.selectors.order_selector import get_order_by_id_and_user
from luxury_fashion.apps.payments.selectors.payment_selector import (
    get_open_payment_for_order,
    get_payment_by_asaas_id,
    get_payment_by_id_and_user,
    get_payments_by_order,
)

from luxury_fashion.apps.payments.repositories.payment_repository import create_payment, update_payment
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

        due_date = date.today() + timedelta(days=settings.ASAAS_PAYMENT_DUE_DAYS)

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
    cpf_cnpj = data.credit_card_holder_info.cpf_cnpj if data.credit_card_holder_info else None
    customer_id = _get_or_create_asaas_customer(user_id, cpf_cnpj=cpf_cnpj)

    asaas = AsaasClient()
    credit_card = data.credit_card.model_dump(by_alias=False) if data.credit_card else None
    credit_card_holder_info = (data.credit_card_holder_info.model_dump(by_alias=False) if data.credit_card_holder_info else None)

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
    payment = update_payment(payment, **map_payment_creation_response(response))

    if data.billing_type.value == Payment.PaymentMode.PIX:
        pix_data = asaas.get_pix_qrcode(payment.asaas_payment_id)
        payment = update_payment(payment, **map_pix_qrcode_response(pix_data))

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


def refund_payment(user_id: uuid.UUID, payment_id: uuid.UUID, value: Decimal | None, description: str | None) -> PaymentOut:
    payment = get_payment_by_id_and_user(payment_id=payment_id, user_id=user_id)
    if payment is None:
        raise PaymentNotFound()

    if payment.status not in _REFUNDABLE_STATUSES or payment.billing_type not in _REFUNDABLE_BILLING_TYPES:
        raise PaymentNotRefundable()

    asaas = AsaasClient()
    response = asaas.refund_payment(payment.asaas_payment_id, value=value, description=description)
    payment = update_payment(payment, **map_refund_response(response))
    return PaymentOut.from_orm(payment)


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
        completed_order(order=order)
    elif status in _REFUND_STATUSES and order.order_status != Order.StatusOrder.REFUNDED:
        refunded_order(order=order)