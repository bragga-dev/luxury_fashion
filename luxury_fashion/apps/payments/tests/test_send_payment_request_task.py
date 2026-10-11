"""
Testes da task `send_payment_request`. A task é chamada diretamente como
função (não via `.delay()`), o que já pula completamente a camada de
transporte do Celery — não depende de broker/result backend disponível.
"""
import uuid

import pytest
from django.core import mail

from luxury_fashion.apps.payments.tasks.send_payment_request import send_payment_request

pytestmark = pytest.mark.django_db


class TestSendPaymentRequestTask:
    def test_sends_email_when_everything_exists(self, user, client_profile, pending_payment, asaas_customer):
        send_payment_request(user.user_id, pending_payment.payment_id)

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == [user.email]
        assert "Pagamento" in sent.subject

    def test_missing_user_does_not_send_and_does_not_raise(self, pending_payment):
        send_payment_request(uuid.uuid4(), pending_payment.payment_id)
        assert len(mail.outbox) == 0

    def test_missing_payment_does_not_send_and_does_not_raise(self, user):
        send_payment_request(user.user_id, uuid.uuid4())
        assert len(mail.outbox) == 0

    def test_missing_asaas_customer_does_not_send_and_does_not_raise(self, user, client_profile, pending_payment):
        # client_profile existe mas não tem AsaasCustomer associado.
        send_payment_request(user.user_id, pending_payment.payment_id)
        assert len(mail.outbox) == 0
