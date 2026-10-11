"""
Testes do mapper — tradução das respostas cruas da Asaas pros campos do
Payment. Puramente funcional, sem banco e sem rede.
"""
from django.utils import timezone

from luxury_fashion.apps.payments.services.asaas_payment_mapper import (
    map_payment_creation_response,
    map_pix_qrcode_response,
    map_refund_response,
    map_webhook_payment_data,
)


class TestMapPaymentCreationResponse:
    def test_maps_known_fields(self):
        response = {
            "id": "pay_123",
            "status": "PENDING",
            "invoiceUrl": "https://asaas.com/i/123",
            "bankSlipUrl": "https://asaas.com/b/123",
        }
        fields = map_payment_creation_response(response)
        assert fields == {
            "synced_with_asaas": True,
            "asaas_payment_id": "pay_123",
            "status": "PENDING",
            "invoice_url": "https://asaas.com/i/123",
            "bank_slip_url": "https://asaas.com/b/123",
        }

    def test_ignores_absent_optional_fields(self):
        fields = map_payment_creation_response({"id": "pay_123", "status": "PENDING"})
        assert "invoice_url" not in fields
        assert "bank_slip_url" not in fields
        assert fields["synced_with_asaas"] is True


class TestMapPixQrcodeResponse:
    def test_maps_encoded_image_and_payload(self):
        fields = map_pix_qrcode_response({"encodedImage": "aGVsbG8=", "payload": "00020126..."})
        assert fields == {"pix_qr_code": "aGVsbG8=", "pix_copy_paste": "00020126..."}

    def test_empty_response_yields_no_fields(self):
        assert map_pix_qrcode_response({}) == {}


class TestMapWebhookPaymentData:
    def test_maps_status_payment_date_and_net_value(self):
        fields = map_webhook_payment_data(
            "RECEIVED",
            {"paymentDate": "2026-01-15", "netValue": 95.5},
        )
        assert fields["status"] == "RECEIVED"
        assert fields["net_value"] == 95.5
        assert fields["payment_date"].year == 2026
        assert fields["payment_date"].month == 1
        assert fields["payment_date"].day == 15
        assert timezone.is_aware(fields["payment_date"])

    def test_prefers_payment_date_over_client_payment_date(self):
        fields = map_webhook_payment_data(
            "RECEIVED",
            {"paymentDate": "2026-02-01", "clientPaymentDate": "2026-02-05"},
        )
        assert fields["payment_date"].day == 1

    def test_falls_back_to_client_payment_date(self):
        fields = map_webhook_payment_data(
            "RECEIVED",
            {"clientPaymentDate": "2026-02-05"},
        )
        assert fields["payment_date"].day == 5

    def test_without_dates_only_status_is_returned(self):
        fields = map_webhook_payment_data("OVERDUE", {})
        assert fields == {"status": "OVERDUE"}


class TestMapRefundResponse:
    def test_uses_response_status(self):
        assert map_refund_response({"status": "REFUNDED"}) == {"status": "REFUNDED"}

    def test_defaults_to_refunded_when_missing(self):
        assert map_refund_response({}) == {"status": "REFUNDED"}
