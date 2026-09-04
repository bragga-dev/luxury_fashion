"""
Payment Service — orquestra a criação/consulta/estorno de cobranças na
Asaas e a aplicação do webhook. Fala com o AsaasClient; repositories só
persistem o que o service já decidiu.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings

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
from luxury_fashion.apps.payments.repositories.order_repository import update_order_status
from luxury_fashion.apps.payments.repositories.payment_repository import (
    apply_asaas_response,
    apply_pix_qrcode,
    create_payment,
    update_status_from_webhook,
)
from luxury_fashion.apps.payments.schemas.payment_schema import PaymentCreateIn, PaymentOut
from luxury_fashion.apps.payments.selectors.order_selector import get_order_by_id_and_user
from luxury_fashion.apps.payments.selectors.payment_selector import (
    get_open_payment_for_order,
    get_payment_by_asaas_id,
    get_payment_by_id_and_user,
    get_payments_by_order,
)

# status da Asaas que contam como "cobrança paga" pro pedido
_PAID_STATUSES = {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"}
_REFUND_STATUSES = {"REFUNDED"}
_REFUNDABLE_STATUSES = {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"}
_REFUNDABLE_BILLING_TYPES = {Payment.PaymentMode.PIX, Payment.PaymentMode.CREDIT_CARD}


def _get_or_create_asaas_customer(user_id: uuid.UUID, cpf_cnpj: str | None = None) -> str:
    client = get_client_by_user_id(user_id)
    if client.asaas_customer_id:
        return client.asaas_customer_id

    if not (cpf_cnpj or client.cpf):
        raise CpfOrCnpjRequired()

    asaas = AsaasClient()
    response = asaas.create_customer(
        name=client.get_full_name(),
        cpf_cnpj=cpf_cnpj or client.cpf,
        email=client.user_id.email,
        external_reference=str(client.client_id),
    )
    # set_client_asaas_customer_id(client, response["id"])
    return response["id"]


def create_payment_for_order(user_id: uuid.UUID, order_id: uuid.UUID, data: PaymentCreateIn) -> PaymentOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()

    if order.order_status != Order.StatusOrder.PENDING:
        raise OrderNotPayable()

    if get_open_payment_for_order(order.order_id) is not None:
        raise OrderAlreadyPaid()

    cpf_cnpj = data.credit_card_holder_info.cpf_cnpj if data.credit_card_holder_info else None
    customer_id = _get_or_create_asaas_customer(user_id, cpf_cnpj=cpf_cnpj)

    due_date = date.today() + timedelta(days=settings.ASAAS_PAYMENT_DUE_DAYS)

    payment = create_payment(
        order=order,
        billing_type=data.billing_type.value,
        value=order.total_geral,
        due_date=due_date,
        description=f"Pedido {order.code}",
        external_reference=str(order.order_id),
    )

    asaas = AsaasClient()
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
    payment = apply_asaas_response(payment, response)

    if data.billing_type.value == Payment.PaymentMode.PIX:
        pix_data = asaas.get_pix_qrcode(payment.asaas_payment_id)
        payment = apply_pix_qrcode(payment, pix_data)

    update_order_status(order, Order.StatusOrder.PROCESSING)

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
    payment = update_status_from_webhook(payment, response.get("status", "REFUNDED"))
    return PaymentOut.from_orm(payment)


def handle_asaas_webhook(token: str, event: str, payment_data: dict) -> None:
    if not settings.ASAAS_WEBHOOK_TOKEN or token != settings.ASAAS_WEBHOOK_TOKEN:
        raise InvalidWebhookToken()

    asaas_payment_id = payment_data.get("id")
    if not asaas_payment_id:
        return

    payment = get_payment_by_asaas_id(asaas_payment_id)
    if payment is None:
        # cobrança que a gente não gerou (ou já foi limpa) — ignora
        return

    status = payment_data.get("status")
    if not status:
        return

    payment = update_status_from_webhook(payment, status, payment_data)

    order = payment.order_id
    if status in _PAID_STATUSES and order.order_status != Order.StatusOrder.COMPLETED:
        update_order_status(order, Order.StatusOrder.COMPLETED)
    elif status in _REFUND_STATUSES:
        update_order_status(order, Order.StatusOrder.REFUNDED)