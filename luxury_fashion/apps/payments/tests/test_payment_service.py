"""
Testes do Payment Service — a Asaas é sempre mockada (nunca sai pra rede
de verdade). Cobrem o fluxo feliz e, principalmente, os dois bugs
corrigidos:

1. Falha na criação da cobrança na Asaas não pode deixar um Payment
   "PENDING" travando pra sempre as tentativas seguintes no mesmo pedido.
2. Falha ao buscar o QR Code Pix (depois que a cobrança já existe na
   Asaas) não pode derrubar a criação inteira.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from luxury_fashion.apps.core.exceptions import (
    AsaasAPIError,
    CpfOrCnpjRequired,
    OrderAlreadyPaid,
    OrderNotFound,
    OrderNotPayable,
    PaymentNotFound,
    PaymentNotRefundable,
)
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.schemas.payment_schema import (
    PaymentBillingTypeEnum,
    PaymentCreateIn,
)
from luxury_fashion.apps.payments.services import payment_service

pytestmark = pytest.mark.django_db


def _fake_asaas(monkeypatch, **method_overrides):
    """Substitui AsaasClient usado dentro do service por um MagicMock."""
    fake_instance = MagicMock()
    fake_instance.create_payment.return_value = {
        "id": "pay_new_001",
        "status": "PENDING",
        "invoiceUrl": "https://sandbox.asaas.com/i/pay_new_001",
    }
    fake_instance.get_pix_qrcode.return_value = {
        "encodedImage": "aGVsbG8=",
        "payload": "00020126...",
    }
    fake_instance.create_customer.return_value = {"id": "cus_new_001"}
    fake_instance.refund_payment.return_value = {"status": "REFUNDED"}
    for name, value in method_overrides.items():
        getattr(fake_instance, name).side_effect = value

    fake_class = MagicMock(return_value=fake_instance)
    monkeypatch.setattr(payment_service, "AsaasClient", fake_class)
    return fake_instance


class TestCreatePaymentForOrder:
    def test_creates_pix_payment_happy_path(
        self, monkeypatch, django_capture_on_commit_callbacks, user, client_profile, order, asaas_customer
    ):
        fake_asaas = _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)

        with django_capture_on_commit_callbacks(execute=True):
            result = payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

        assert result.asaas_payment_id == "pay_new_001"
        assert result.pix_qr_code == "aGVsbG8="
        assert result.pix_copy_paste == "00020126..."
        fake_asaas.create_payment.assert_called_once()
        fake_asaas.get_pix_qrcode.assert_called_once_with("pay_new_001")
        # Cliente já tinha AsaasCustomer -> não deveria criar outro.
        fake_asaas.create_customer.assert_not_called()

        order.refresh_from_db()
        payment = Payment.objects.get(order_id=order)
        assert payment.status == "PENDING"
        assert payment.synced_with_asaas is True

    def test_creates_asaas_customer_when_missing(
        self, monkeypatch, django_capture_on_commit_callbacks, user, client_profile, order
    ):
        fake_asaas = _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)

        with django_capture_on_commit_callbacks(execute=True):
            payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

        fake_asaas.create_customer.assert_called_once()
        call_kwargs = fake_asaas.create_customer.call_args.kwargs
        assert call_kwargs["cpf_cnpj"] == client_profile.cpf

    def test_boleto_does_not_fetch_pix_qrcode(
        self, monkeypatch, django_capture_on_commit_callbacks, user, client_profile, order, asaas_customer
    ):
        fake_asaas = _fake_asaas(monkeypatch)
        fake_asaas.create_payment.return_value = {
            "id": "pay_boleto_001",
            "status": "PENDING",
            "bankSlipUrl": "https://sandbox.asaas.com/b/pay_boleto_001",
        }
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.BOLETO)

        with django_capture_on_commit_callbacks(execute=True):
            result = payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

        fake_asaas.get_pix_qrcode.assert_not_called()
        assert result.bank_slip_url == "https://sandbox.asaas.com/b/pay_boleto_001"

    def test_missing_order_raises_order_not_found(self, monkeypatch, user):
        _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        with pytest.raises(OrderNotFound):
            payment_service.create_payment_for_order(user.user_id, "00000000-0000-0000-0000-000000000000", payload)

    def test_order_of_another_user_is_not_found(self, monkeypatch, other_user, order):
        _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        with pytest.raises(OrderNotFound):
            payment_service.create_payment_for_order(other_user.user_id, order.order_id, payload)

    def test_non_pending_order_is_not_payable(self, monkeypatch, user, order):
        _fake_asaas(monkeypatch)
        order.order_status = Order.StatusOrder.COMPLETED
        order.save(update_fields=["order_status"])
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        with pytest.raises(OrderNotPayable):
            payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

    def test_existing_open_payment_blocks_new_charge(self, monkeypatch, user, order, pending_payment):
        _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        with pytest.raises(OrderAlreadyPaid):
            payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

    def test_requires_cpf_when_client_has_none_and_none_provided(
        self, monkeypatch, user, client_profile, order
    ):
        client_profile.cpf = None
        client_profile.save()
        _fake_asaas(monkeypatch)
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        with pytest.raises(CpfOrCnpjRequired):
            payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

    def test_asaas_failure_on_creation_cancels_local_payment_and_unblocks_retry(
        self, monkeypatch, user, client_profile, order, asaas_customer
    ):
        """Bug corrigido: cobrança que falha na Asaas não pode travar o pedido pra sempre."""
        fake_asaas = _fake_asaas(
            monkeypatch,
            create_payment=AsaasAPIError("Falha simulada na Asaas"),
        )
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)

        with pytest.raises(AsaasAPIError):
            payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

        payment = Payment.objects.get(order_id=order)
        assert payment.status == Payment.PaymentStatus.CANCELLED
        assert payment.asaas_payment_id is None

        # Sem isso, a linha abaixo levantaria OrderAlreadyPaid pra sempre.
        fake_asaas.create_payment.side_effect = None
        fake_asaas.create_payment.return_value = {"id": "pay_retry_001", "status": "PENDING"}
        result = payment_service.create_payment_for_order(user.user_id, order.order_id, payload)
        assert result.asaas_payment_id == "pay_retry_001"

    def test_pix_qrcode_failure_does_not_break_payment_creation(
        self, monkeypatch, django_capture_on_commit_callbacks, user, client_profile, order, asaas_customer
    ):
        """Bug corrigido: a cobrança já existe na Asaas, só o QR falhou — não deve dar 502."""
        fake_asaas = _fake_asaas(
            monkeypatch,
            get_pix_qrcode=AsaasAPIError("Falha simulada ao buscar QR Code"),
        )
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)

        with django_capture_on_commit_callbacks(execute=True):
            result = payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

        assert result.asaas_payment_id == "pay_new_001"
        assert result.status == "PENDING"
        assert result.pix_qr_code is None
        assert result.pix_copy_paste is None

        payment = Payment.objects.get(order_id=order)
        assert payment.status == "PENDING"


class TestGetAndListPayments:
    def test_get_payment_for_client_returns_owned_payment(self, user, pending_payment):
        result = payment_service.get_payment_for_client(user.user_id, pending_payment.payment_id)
        assert result.payment_id == pending_payment.payment_id

    def test_get_payment_for_other_user_is_not_found(self, other_user, pending_payment):
        with pytest.raises(PaymentNotFound):
            payment_service.get_payment_for_client(other_user.user_id, pending_payment.payment_id)

    def test_list_payments_for_order(self, user, order, pending_payment):
        results = payment_service.list_payments_for_order(user.user_id, order.order_id)
        assert [p.payment_id for p in results] == [pending_payment.payment_id]

    def test_list_payments_for_missing_order_raises(self, user):
        with pytest.raises(OrderNotFound):
            payment_service.list_payments_for_order(user.user_id, "00000000-0000-0000-0000-000000000000")


class TestRefundPayment:
    def test_refunds_a_received_pix_payment(self, monkeypatch, user, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])
        fake_asaas = _fake_asaas(monkeypatch)

        result = payment_service.refund_payment(user.user_id, pending_payment.payment_id, None, None)

        assert result.status == "REFUNDED"
        fake_asaas.refund_payment.assert_called_once_with(
            pending_payment.asaas_payment_id, value=None, description=None
        )

    def test_cannot_refund_pending_payment(self, monkeypatch, user, pending_payment):
        _fake_asaas(monkeypatch)
        with pytest.raises(PaymentNotRefundable):
            payment_service.refund_payment(user.user_id, pending_payment.payment_id, None, None)

    def test_cannot_refund_boleto(self, monkeypatch, user, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.billing_type = Payment.PaymentMode.BOLETO
        pending_payment.save(update_fields=["status", "billing_type"])
        _fake_asaas(monkeypatch)
        with pytest.raises(PaymentNotRefundable):
            payment_service.refund_payment(user.user_id, pending_payment.payment_id, None, None)

    def test_refund_missing_payment_raises(self, monkeypatch, user):
        _fake_asaas(monkeypatch)
        with pytest.raises(PaymentNotFound):
            payment_service.refund_payment(user.user_id, "00000000-0000-0000-0000-000000000000", None, None)


class TestHandleAsaasWebhook:
    def test_invalid_token_is_rejected(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        from luxury_fashion.apps.core.exceptions import InvalidWebhookToken

        with pytest.raises(InvalidWebhookToken):
            payment_service.handle_asaas_webhook(
                token="token-errado",
                event="PAYMENT_RECEIVED",
                payment_data={"id": pending_payment.asaas_payment_id, "status": "RECEIVED"},
            )

    def test_unset_webhook_token_rejects_everything(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = ""
        from luxury_fashion.apps.core.exceptions import InvalidWebhookToken

        with pytest.raises(InvalidWebhookToken):
            payment_service.handle_asaas_webhook(
                token="", event="PAYMENT_RECEIVED", payment_data={"id": pending_payment.asaas_payment_id}
            )

    def test_updates_payment_and_completes_order_on_received(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        payment_service.handle_asaas_webhook(
            token="token-correto",
            event="PAYMENT_RECEIVED",
            payment_data={
                "id": pending_payment.asaas_payment_id,
                "status": "RECEIVED",
                "paymentDate": "2026-01-10",
                "netValue": 210.0,
            },
        )
        pending_payment.refresh_from_db()
        assert pending_payment.status == "RECEIVED"
        assert float(pending_payment.net_value) == 210.0

        pending_payment.order_id.refresh_from_db()
        assert pending_payment.order_id.order_status == Order.StatusOrder.COMPLETED

    def test_completing_an_already_completed_order_is_idempotent(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        order = pending_payment.order_id
        order.complete()

        # Não deve levantar InvalidOrderStatusTransition numa segunda notificação.
        payment_service.handle_asaas_webhook(
            token="token-correto",
            event="PAYMENT_RECEIVED",
            payment_data={"id": pending_payment.asaas_payment_id, "status": "RECEIVED"},
        )
        order.refresh_from_db()
        assert order.order_status == Order.StatusOrder.COMPLETED

    def test_refund_status_refunds_completed_order(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        pending_payment.order_id.complete()

        payment_service.handle_asaas_webhook(
            token="token-correto",
            event="PAYMENT_REFUNDED",
            payment_data={"id": pending_payment.asaas_payment_id, "status": "REFUNDED"},
        )
        pending_payment.order_id.refresh_from_db()
        assert pending_payment.order_id.order_status == Order.StatusOrder.REFUNDED

    def test_unknown_payment_id_is_ignored_silently(self, settings):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        payment_service.handle_asaas_webhook(
            token="token-correto",
            event="PAYMENT_RECEIVED",
            payment_data={"id": "pay_does_not_exist", "status": "RECEIVED"},
        )

    def test_missing_payment_id_is_ignored(self, settings):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        payment_service.handle_asaas_webhook(token="token-correto", event="PAYMENT_RECEIVED", payment_data={})

    def test_missing_status_is_ignored(self, settings, pending_payment):
        settings.ASAAS_WEBHOOK_TOKEN = "token-correto"
        payment_service.handle_asaas_webhook(
            token="token-correto",
            event="PAYMENT_RECEIVED",
            payment_data={"id": pending_payment.asaas_payment_id},
        )
        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.PaymentStatus.PENDING
