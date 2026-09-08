"""
Mapper — traduz respostas cruas da Asaas (JSON em camelCase, campos que
podem ou não vir preenchidos) pros campos que o Payment entende.

É o único lugar fora do AsaasClient que sabe que a Asaas existe e como ela
formata as coisas. O repository não entra aqui — ele só recebe o dict
pronto e grava. O service usa essas funções pra montar o que vai persistir.
"""
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def _to_aware_datetime(raw: str):
    parsed = parse_datetime(raw) or parse_date(raw)
    if parsed is None:
        return None
    if not hasattr(parsed, "hour"): 
        parsed = timezone.datetime.combine(parsed, timezone.datetime.min.time())
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def map_payment_creation_response(response: dict) -> dict:
    """POST /payments da Asaas -> campos do Payment logo após criar a cobrança."""
    fields = {"synced_with_asaas": True}
    if response.get("id"):
        fields["asaas_payment_id"] = response["id"]
    if response.get("status"):
        fields["status"] = response["status"]
    if response.get("invoiceUrl"):
        fields["invoice_url"] = response["invoiceUrl"]
    if response.get("bankSlipUrl"):
        fields["bank_slip_url"] = response["bankSlipUrl"]
    return fields


def map_pix_qrcode_response(response: dict) -> dict:
    """GET /payments/{id}/pixQrCode -> campos de exibição do Pix."""
    fields = {}
    if response.get("encodedImage"):
        fields["pix_qr_code"] = response["encodedImage"]
    if response.get("payload"):
        fields["pix_copy_paste"] = response["payload"]
    return fields


def map_webhook_payment_data(status: str, payment_data: dict) -> dict:
    """Corpo do webhook -> status + data de pagamento + valor líquido."""
    fields = {"status": status}

    payment_date_raw = payment_data.get("paymentDate") or payment_data.get("clientPaymentDate")
    if payment_date_raw:
        parsed = _to_aware_datetime(payment_date_raw)
        if parsed is not None:
            fields["payment_date"] = parsed

    net_value = payment_data.get("netValue")
    if net_value is not None:
        fields["net_value"] = net_value

    return fields


def map_refund_response(response: dict) -> dict:
    """POST /payments/{id}/refund -> status pós-estorno."""
    return {"status": response.get("status", "REFUNDED")}