"""
Testes do Order Repository — persistência pura de Order/OrderItem e as
transições de status delegadas ao model (`Order.cancel/complete/fail/refund`).
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.repositories.order_repository import (
    bulk_create_order_items,
    canceled_order,
    completed_order,
    create_order,
    failed_order,
    refunded_order,
)

pytestmark = pytest.mark.django_db


class TestCreateOrder:
    def test_creates_and_persists_order(self, user, address):
        order = create_order(
            user=user,
            shipping_address=address,
            subtotal=Decimal("100.00"),
            order_shipping_total=Decimal("10.00"),
            total_geral=Decimal("110.00"),
        )

        assert order.pk is not None
        assert Order.objects.filter(order_id=order.order_id).exists()
        assert order.order_status == Order.StatusOrder.PENDING
        assert order.total_geral == Decimal("110.00")

    def test_runs_full_clean_before_saving(self, user, address):
        # subtotal estoura max_digits=10 -> full_clean deve rejeitar antes do save.
        with pytest.raises(ValidationError):
            create_order(
                user=user,
                shipping_address=address,
                subtotal=Decimal("999999999999.00"),
                order_shipping_total=Decimal("0.00"),
                total_geral=Decimal("0.00"),
            )
        assert not Order.objects.filter(subtotal=Decimal("999999999999.00")).exists()


class TestBulkCreateOrderItems:
    def test_creates_one_item_per_entry(self, order, variant, other_variant):
        items = bulk_create_order_items(
            order=order,
            items=[
                {"variant": variant, "quantity": 2, "unit_price": variant.price},
                {"variant": other_variant, "quantity": 1, "unit_price": other_variant.price},
            ],
        )

        assert len(items) == 2
        assert OrderItem.objects.filter(order_id=order).count() == 2

    def test_runs_full_clean_on_each_item(self, order, variant):
        with pytest.raises(ValidationError):
            bulk_create_order_items(
                order=order,
                items=[{"variant": variant, "quantity": 0, "unit_price": variant.price}],
            )


class TestOrderStatusTransitions:
    def test_completed_order_marks_order_completed(self, order):
        result = completed_order(order=order)
        assert result.order_status == Order.StatusOrder.COMPLETED
        order.refresh_from_db()
        assert order.completed_at is not None

    def test_canceled_order_marks_order_cancelled_with_reason(self, order):
        result = canceled_order(order=order, reason="Cliente desistiu")
        assert result.order_status == Order.StatusOrder.CANCELLED
        order.refresh_from_db()
        assert order.canceled_reason == "Cliente desistiu"

    def test_failed_order_marks_order_failed(self, order):
        result = failed_order(order=order)
        assert result.order_status == Order.StatusOrder.FAILED

    def test_refunded_order_marks_order_refunded(self, order):
        order.complete()
        result = refunded_order(order=order)
        assert result.order_status == Order.StatusOrder.REFUNDED