"""
Testes do webhook público da Asaas — sem auth JWT (é a Asaas quem chama),
protegido pelo token no header `asaas-access-token`.
"""
import pytest

from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment

pytestmark = pytest.mark.django_db

WEBHOOK_URL = "/api/webhooks/asaas/"


class TestAsaasWebhookEndpoint:
    def test_valid_token_updates_payment(self, client, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        resp = client.post(
            WEBHOOK_URL,
            data={
                "event": "PAYMENT_RECEIVED",
                "payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"},
            },
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="token-correto",
        )
        assert resp.status_code == 200
        pending_payment.refresh_from_db()
        assert pending_payment.status == "RECEIVED"

    def test_invalid_token_returns_401(self, client, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        resp = client.post(
            WEBHOOK_URL,
            data={
                "event": "PAYMENT_RECEIVED",
                "payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"},
            },
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="token-errado",
        )
        assert resp.status_code == 401
        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.PaymentStatus.PENDING

    def test_missing_token_header_returns_401(self, client, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        resp = client.post(
            WEBHOOK_URL,
            data={
                "event": "PAYMENT_RECEIVED",
                "payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"},
            },
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_unknown_payment_still_returns_200(self, client, settings):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        resp = client.post(
            WEBHOOK_URL,
            data={"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_inexistente", "status": "RECEIVED"}},
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="token-correto",
        )
        assert resp.status_code == 200

    def test_refund_event_refunds_completed_order(self, client, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        pending_payment.order_id.complete()

        resp = client.post(
            WEBHOOK_URL,
            data={
                "event": "PAYMENT_REFUNDED",
                "payment": {"id": pending_payment.asaas_payment_id, "status": "REFUNDED"},
            },
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="token-correto",
        )
        assert resp.status_code == 200
        pending_payment.order_id.refresh_from_db()
        assert pending_payment.order_id.order_status == Order.StatusOrder.REFUNDED

    def test_malformed_body_returns_422(self, client, settings):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        resp = client.post(
            WEBHOOK_URL,
            data={"event": "PAYMENT_RECEIVED"},  # falta "payment"
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN="token-correto",
        )
        assert resp.status_code == 422
