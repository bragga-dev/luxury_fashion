"""
Order Service — orquestra o checkout: carrinho do cliente autenticado vira
Order + OrderItems, o estoque é baixado e o carrinho é esvaziado.
"""
import uuid
from decimal import Decimal

from luxury_fashion.apps.accounts.selectors.address_selector import get_address_by_id
from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.cart.repositories.cart_item_repository import clear_cart
from luxury_fashion.apps.cart.selectors.cart_item_selector import get_items_by_cart
from luxury_fashion.apps.cart.selectors.cart_selector import get_cart_by_user_id
from luxury_fashion.apps.core.exceptions import EmptyCart, OrderNotFound, UserNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.accounts.selectors.user_selector import get_user_by_id
from luxury_fashion.apps.payments.repositories.order_repository import (
    bulk_create_order_items,
    create_order,
    update_order_status,
)
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn, OrderOut
from luxury_fashion.apps.payments.selectors.order_selector import (
    get_order_by_id_and_user,
    get_orders_by_user,
)
from luxury_fashion.apps.products.repositories.product_variant_repository import adjust_variant_stock


def _validate_shipping_address(user_id: uuid.UUID, shipping_address_id: uuid.UUID):
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise UserNotFound()

    address = get_address_by_id(shipping_address_id=shipping_address_id)
    if address is None or address.client_id_id != client.client_id:
        raise PermissionDenied("Endereço não pertence ao cliente autenticado.")
    return address


def create_order_from_cart(user_id: uuid.UUID, data: OrderCreateIn) -> OrderOut:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()

    shipping_address = _validate_shipping_address(user_id=user_id, shipping_address_id=data.shipping_address_id)

    cart = get_cart_by_user_id(user_id=user_id)
    if cart is None:
        raise EmptyCart()

    cart_items = list(get_items_by_cart(cart_id=cart.cart_id))
    if not cart_items:
        raise EmptyCart()

    for item in cart_items:
        if item.quantity_item > item.variant_id.stock:
            raise InsufficientStock(
                f"Estoque insuficiente para {item.variant_id}."
            )

    order = create_order(
        user=user,
        shipping_address=shipping_address,
        subtotal=cart.total_price,
        order_shipping_total=cart.total_shipping,
        total_geral=cart.total_geral,
    )

    bulk_create_order_items(
        order=order,
        items=[
            {
                "variant": item.variant_id,
                "quantity": item.quantity_item,
                "unit_price": item.unit_price_item,
            }
            for item in cart_items
        ],
    )

    for item in cart_items:
        adjust_variant_stock(variant=item.variant_id, delta=-item.quantity_item)

    clear_cart(cart=cart)

    return _order_out_for(user_id=user_id, order_id=order.order_id)


def _order_out_for(user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    return OrderOut.from_orm(order)


def get_order_for_client(user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()
    return OrderOut.from_orm(order)


def list_orders_for_client(user_id: uuid.UUID) -> list[OrderOut]:
    orders = get_orders_by_user(user_id=user_id)
    return [OrderOut.from_orm(order) for order in orders]


def cancel_order(user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
    """
    Cancela um pedido ainda pendente e devolve o estoque reservado.
    Pedidos já pagos/em processamento não são cancelados por aqui — isso
    passa pelo fluxo de estorno de pagamento.
    """
    from luxury_fashion.apps.core.exceptions import OrderNotPayable
    from luxury_fashion.apps.payments.models.order_model import Order

    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()

    if order.order_status != Order.StatusOrder.PENDING:
        raise OrderNotPayable("Só é possível cancelar pedidos com pagamento pendente.")

    for item in order.items.all():
        adjust_variant_stock(variant=item.variant_id, delta=item.order_item_quantity)

    update_order_status(order, Order.StatusOrder.CANCELLED)
    return _order_out_for(user_id=user_id, order_id=order_id)