"""
Testes do Order Service — orquestração do checkout (carrinho -> Order) e
das operações de consulta/cancelamento de pedidos do cliente autenticado.
"""
import uuid
from decimal import Decimal

import pytest

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.core.exceptions import EmptyCart, OrderNotFound, OrderNotPayable, UserNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn
from luxury_fashion.apps.payments.services.order_service import (
    cancel_order_by_client,
    create_order_from_cart,
    get_order_for_client,
    list_orders_for_client,
)

pytestmark = pytest.mark.django_db


class TestCreateOrderFromCart:
    def test_creates_order_from_cart_items_and_debits_stock(self, user, client_profile, address, cart, cart_item, variant):
        payload = OrderCreateIn(shipping_address_id=address.address_id)

        result = create_order_from_cart(user_id=user.user_id, data=payload)

        assert result.order_status.value == Order.StatusOrder.PENDING
        assert len(result.items) == 1
        assert result.items[0].order_item_quantity == cart_item.quantity_item

        variant.refresh_from_db()
        assert variant.stock == 5 - cart_item.quantity_item

    def test_clears_the_cart_after_checkout(self, user, client_profile, address, cart, cart_item):
        payload = OrderCreateIn(shipping_address_id=address.address_id)
        create_order_from_cart(user_id=user.user_id, data=payload)

        cart.refresh_from_db()
        assert cart.items.count() == 0
        assert cart.total_geral == Decimal("0.00")

    def test_raises_user_not_found_when_user_does_not_exist(self, address):
        payload = OrderCreateIn(shipping_address_id=address.address_id)
        with pytest.raises(UserNotFound):
            create_order_from_cart(user_id=uuid.uuid4(), data=payload)

    def test_raises_user_not_found_when_user_has_no_client_profile(self, other_user, address):
        payload = OrderCreateIn(shipping_address_id=address.address_id)
        with pytest.raises(UserNotFound):
            create_order_from_cart(user_id=other_user.user_id, data=payload)

    def test_raises_permission_denied_when_address_does_not_exist(self, user, client_profile):
        payload = OrderCreateIn(shipping_address_id=uuid.uuid4())
        with pytest.raises(PermissionDenied):
            create_order_from_cart(user_id=user.user_id, data=payload)

    def test_raises_permission_denied_when_address_belongs_to_another_client(
        self, user, client_profile, other_user
    ):
        from luxury_fashion.apps.accounts.models.client_model import Client

        other_client = Client(user_id=other_user, first_name="Outro", last_name="Cliente")
        other_client.cpf = "98765432100"
        other_client.save()
        foreign_address = AddressesClient.objects.create(
            client_id=other_client,
            cep="45200-000",
            street="Rua Alheia",
            number="1",
            neighborhood="Centro",
            city="Jequié",
            state="BA",
        )

        payload = OrderCreateIn(shipping_address_id=foreign_address.address_id)
        with pytest.raises(PermissionDenied):
            create_order_from_cart(user_id=user.user_id, data=payload)

    def test_raises_empty_cart_when_user_has_no_cart(self, user, client_profile, address):
        payload = OrderCreateIn(shipping_address_id=address.address_id)
        with pytest.raises(EmptyCart):
            create_order_from_cart(user_id=user.user_id, data=payload)

    def test_raises_empty_cart_when_cart_has_no_items(self, user, client_profile, address, cart):
        payload = OrderCreateIn(shipping_address_id=address.address_id)
        with pytest.raises(EmptyCart):
            create_order_from_cart(user_id=user.user_id, data=payload)

    def test_raises_insufficient_stock_when_quantity_exceeds_stock(
        self, user, client_profile, address, cart, variant
    ):
        from luxury_fashion.apps.cart.models.cart_item_model import CartItem

        CartItem.objects.create(cart_id=cart, variant_id=variant, quantity_item=variant.stock + 1)

        payload = OrderCreateIn(shipping_address_id=address.address_id)
        with pytest.raises(InsufficientStock):
            create_order_from_cart(user_id=user.user_id, data=payload)

        variant.refresh_from_db()
        assert variant.stock == 5  # nada foi debitado


class TestGetOrderForClient:
    def test_returns_order_owned_by_user(self, order, user):
        result = get_order_for_client(user_id=user.user_id, order_id=order.order_id)
        assert result.order_id == order.order_id

    def test_raises_order_not_found_when_order_belongs_to_another_user(self, order, other_user):
        with pytest.raises(OrderNotFound):
            get_order_for_client(user_id=other_user.user_id, order_id=order.order_id)

    def test_raises_order_not_found_when_order_does_not_exist(self, user):
        with pytest.raises(OrderNotFound):
            get_order_for_client(user_id=user.user_id, order_id=uuid.uuid4())


class TestListOrdersForClient:
    def test_lists_only_orders_of_the_given_user(self, user, address, other_user):
        Order.objects.create(user_id=user, shipping_address=address, total_geral=Decimal("10.00"))
        Order.objects.create(user_id=other_user, shipping_address=address, total_geral=Decimal("20.00"))

        results = list_orders_for_client(user_id=user.user_id)

        assert len(results) == 1

    def test_returns_empty_list_when_no_orders(self, user):
        assert list_orders_for_client(user_id=user.user_id) == []


class TestCancelOrderByClient:
    def test_cancels_pending_order_and_restocks_variant(self, order, user, variant):
        from luxury_fashion.apps.payments.models.order_item_model import OrderItem

        OrderItem.objects.create(
            order_id=order, variant_id=variant, order_item_quantity=2, order_item_price=variant.price
        )
        variant.stock = 0
        variant.save(update_fields=["stock"])

        result = cancel_order_by_client(user_id=user.user_id, order_id=order.order_id, reason="Mudei de ideia")

        assert result.order_status.value == Order.StatusOrder.CANCELLED
        variant.refresh_from_db()
        assert variant.stock == 2

    def test_raises_order_not_found_when_order_belongs_to_another_user(self, order, other_user):
        with pytest.raises(OrderNotFound):
            cancel_order_by_client(user_id=other_user.user_id, order_id=order.order_id)

    def test_raises_order_not_payable_when_order_is_not_pending(self, order, user):
        order.complete()
        with pytest.raises(OrderNotPayable):
            cancel_order_by_client(user_id=user.user_id, order_id=order.order_id)