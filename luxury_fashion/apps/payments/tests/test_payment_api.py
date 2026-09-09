"""
Testes de integração dos endpoints de pagamento — sobem a API Ninja de
verdade (roteamento, auth, schemas, exception handlers) via Django test
client. A Asaas continua mockada; nenhuma chamada de rede acontece.
"""
from unittest.mock import MagicMock

import pytest
from ninja_jwt.tokens import RefreshToken

from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.services import payment_service

pytestmark = pytest.mark.django_db


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _fake_asaas(monkeypatch, **method_overrides):
    fake_instance = MagicMock()
    fake_instance.create_payment.return_value = {"id": "pay_api_001", "status": "PENDING"}
    fake_instance.get_pix_qrcode.return_value = {"encodedImage": "img", "payload": "copia-e-cola"}
    fake_instance.create_customer.return_value = {"id": "cus_api_001"}
    fake_instance.refund_payment.return_value = {"status": "REFUNDED"}
    for name, value in method_overrides.items():
        getattr(fake_instance, name).side_effect = value
    monkeypatch.setattr(payment_service, "AsaasClient", MagicMock(return_value=fake_instance))
    return fake_instance


class TestCreatePaymentEndpoint:
    def test_creates_pix_payment(self, client, monkeypatch, user, client_profile, order, asaas_customer):
        _fake_asaas(monkeypatch)
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["billing_type"] == "PIX"
        assert body["asaas_payment_id"] == "pay_api_001"

    def test_requires_authentication(self, client, order):
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_credit_card_without_card_data_is_rejected(self, client, monkeypatch, user, client_profile, order):
        _fake_asaas(monkeypatch)
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "CREDIT_CARD"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 422

    def test_order_not_found_returns_404(self, client, monkeypatch, user, client_profile):
        _fake_asaas(monkeypatch)
        resp = client.post(
            "/api/orders/00000000-0000-0000-0000-000000000000/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 404

    def test_order_already_paid_returns_409(self, client, monkeypatch, user, client_profile, order, pending_payment):
        _fake_asaas(monkeypatch)
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 409

    def test_asaas_error_returns_502(self, client, monkeypatch, user, client_profile, order, asaas_customer):
        from luxury_fashion.apps.core.exceptions import AsaasAPIError

        _fake_asaas(monkeypatch, create_payment=AsaasAPIError("Indisponível"))
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 502

    def test_unverified_user_is_forbidden(self, client, order):
        from luxury_fashion.apps.accounts.models.user_model import User

        unverified = User.objects.create_user(email="novo@example.com", password="x", is_active=True, is_trusty=False)
        resp = client.post(
            f"/api/orders/{order.order_id}/payments",
            data={"billing_type": "PIX"},
            content_type="application/json",
            **auth_header(unverified),
        )
        assert resp.status_code == 403


class TestGetAndListPaymentsEndpoints:
    def test_get_own_payment(self, client, user, pending_payment):
        resp = client.get(f"/api/payments/{pending_payment.payment_id}", **auth_header(user))
        assert resp.status_code == 200
        assert resp.json()["payment_id"] == str(pending_payment.payment_id)

    def test_cannot_get_payment_of_another_user(self, client, other_user, pending_payment):
        resp = client.get(f"/api/payments/{pending_payment.payment_id}", **auth_header(other_user))
        assert resp.status_code == 404

    def test_list_payments_for_order(self, client, user, order, pending_payment):
        resp = client.get(f"/api/orders/{order.order_id}/payments", **auth_header(user))
        assert resp.status_code == 200
        body = resp.json()
        items = body["items"] if isinstance(body, dict) and "items" in body else body
        assert len(items) == 1
        assert items[0]["payment_id"] == str(pending_payment.payment_id)


class TestRefundEndpoint:
    def test_refunds_received_payment(self, client, monkeypatch, user, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])
        _fake_asaas(monkeypatch)

        resp = client.post(
            f"/api/payments/{pending_payment.payment_id}/refund",
            data={},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REFUNDED"

    def test_refunding_pending_payment_returns_409(self, client, monkeypatch, user, pending_payment):
        _fake_asaas(monkeypatch)
        resp = client.post(
            f"/api/payments/{pending_payment.payment_id}/refund",
            data={},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 409

    def test_refund_of_missing_payment_returns_404(self, client, monkeypatch, user):
        _fake_asaas(monkeypatch)
        resp = client.post(
            "/api/payments/00000000-0000-0000-0000-000000000000/refund",
            data={},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 404

    def test_refund_rejects_non_positive_value(self, client, monkeypatch, user, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])
        _fake_asaas(monkeypatch)
        resp = client.post(
            f"/api/payments/{pending_payment.payment_id}/refund",
            data={"value": 0},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 422
