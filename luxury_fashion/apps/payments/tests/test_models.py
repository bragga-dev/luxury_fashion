"""
Testes de modelo — validações de Payment e as transições de status de
Order. Não envolve Asaas nem service, só as regras que moram no model.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from luxury_fashion.apps.core.exceptions import InvalidOrderStatusTransition
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment

pytestmark = pytest.mark.django_db


def _make_payment(order, **overrides):
    fields = dict(
        order_id=order,
        billing_type=Payment.PaymentMode.PIX,
        value=Decimal("100.00"),
        due_date=date.today() + timedelta(days=1),
        description="Pedido de teste",
    )
    fields.update(overrides)
    payment = Payment(**fields)
    payment.full_clean()
    payment.save()
    return payment


class TestPaymentModel:
    def test_creates_payment_with_defaults(self, order):
        payment = _make_payment(order)
        assert payment.status == Payment.PaymentStatus.PENDING
        assert payment.billing_type == Payment.PaymentMode.PIX
        assert payment.synced_with_asaas is False

    def test_value_must_be_positive(self, order):
        with pytest.raises(ValidationError):
            _make_payment(order, value=Decimal("0.00"))

    def test_negative_value_is_rejected(self, order):
        with pytest.raises(ValidationError):
            _make_payment(order, value=Decimal("-10.00"))

    def test_asaas_payment_id_is_unique(self, order):
        _make_payment(order, asaas_payment_id="pay_dup")
        with pytest.raises(ValidationError):
            _make_payment(order, asaas_payment_id="pay_dup")

    def test_str_includes_order_code(self, order):
        payment = _make_payment(order)
        text = str(payment)
        assert str(payment.payment_id)[:8] in text
        assert order.code in text


class TestOrderTransitions:
    def test_pending_can_complete(self, order):
        order.complete()
        order.refresh_from_db()
        assert order.order_status == Order.StatusOrder.COMPLETED
        assert order.completed_at is not None

    def test_pending_can_cancel_with_reason(self, order):
        order.cancel("Cliente desistiu")
        order.refresh_from_db()
        assert order.order_status == Order.StatusOrder.CANCELLED
        assert order.canceled_reason == "Cliente desistiu"
        assert order.canceled_at is not None

    def test_pending_can_fail(self, order):
        order.fail()
        assert order.order_status == Order.StatusOrder.FAILED

    def test_completed_can_refund(self, order):
        order.complete()
        order.refund()
        assert order.order_status == Order.StatusOrder.REFUNDED

    def test_cancelled_order_cannot_complete(self, order):
        order.cancel("motivo qualquer")
        with pytest.raises(InvalidOrderStatusTransition):
            order.complete()

    def test_completed_order_cannot_cancel(self, order):
        order.complete()
        with pytest.raises(InvalidOrderStatusTransition):
            order.cancel("tarde demais")

    def test_refunded_order_is_terminal(self, order):
        order.complete()
        order.refund()
        with pytest.raises(InvalidOrderStatusTransition):
            order.complete()
        with pytest.raises(InvalidOrderStatusTransition):
            order.refund()

    def test_can_transition_to_reports_false_for_invalid_target(self, order):
        assert order.can_transition_to(Order.StatusOrder.REFUNDED) is False
        assert order.can_transition_to(Order.StatusOrder.COMPLETED) is True
