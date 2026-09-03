"""
Payment Repository — persistência pura de Payment. Nenhuma chamada à Asaas
acontece aqui, só a gravação do que já foi decidido/recebido antes (pelo
service, que fala com o AsaasClient).
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment


def create_payment(
    order: Order,
    billing_type: str,
    value: Decimal,
    due_date: date,
    description: str,
    external_reference: str,
) -> Payment:
    payment = Payment(
        order_id=order,
        billing_type=billing_type,
        value=value,
        due_date=due_date,
        description=description,
        external_reference=external_reference,
    )
    payment.full_clean()
    payment.save()
    return payment


def apply_asaas_response(payment: Payment, data: dict) -> Payment:
    """Preenche o Payment com o retorno da criação da cobrança na Asaas."""
    payment.asaas_payment_id = data.get("id") or payment.asaas_payment_id
    payment.status = data.get("status") or payment.status
    payment.invoice_url = data.get("invoiceUrl") or payment.invoice_url
    payment.bank_slip_url = data.get("bankSlipUrl") or payment.bank_slip_url
    payment.synced_with_asaas = True
    payment.save(update_fields=[
        "asaas_payment_id", "status", "invoice_url", "bank_slip_url",
        "synced_with_asaas", "updated_at",
    ])
    return payment


def apply_pix_qrcode(payment: Payment, data: dict) -> Payment:
    payment.pix_qr_code = data.get("encodedImage") or payment.pix_qr_code
    payment.pix_copy_paste = data.get("payload") or payment.pix_copy_paste
    payment.save(update_fields=["pix_qr_code", "pix_copy_paste", "updated_at"])
    return payment


def _to_aware_datetime(raw: str):
    parsed = parse_datetime(raw) or parse_date(raw)
    if parsed is None:
        return None
    if not hasattr(parsed, "hour"):  
        parsed = timezone.datetime.combine(parsed, timezone.datetime.min.time())
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def update_status_from_webhook(payment: Payment, status: str, data: Optional[dict] = None) -> Payment:
    payment.status = status
    fields = ["status", "updated_at"]

    if data:
        payment_date_raw = data.get("paymentDate") or data.get("clientPaymentDate")
        if payment_date_raw:
            parsed = _to_aware_datetime(payment_date_raw)
            if parsed is not None:
                payment.payment_date = parsed
                fields.append("payment_date")

        net_value = data.get("netValue")
        if net_value is not None:
            payment.net_value = net_value
            fields.append("net_value")

    payment.save(update_fields=fields)
    return payment