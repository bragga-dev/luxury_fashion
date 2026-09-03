"""
Order Repository — persistência pura de Order/OrderItem. Nenhuma regra de
negócio aqui (montar itens a partir do carrinho, validar estoque, etc.) —
isso é responsabilidade do service. O repository só executa a operação de
persistência já decidida e validada antes.
"""
from decimal import Decimal
from typing import Iterable

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order


def create_order(
    user: User,
    shipping_address: AddressesClient,
    subtotal: Decimal,
    order_shipping_total: Decimal,
    total_geral: Decimal,
) -> Order:
    order = Order(
        user_id=user,
        shipping_address=shipping_address,
        subtotal=subtotal,
        order_shipping_total=order_shipping_total,
        total_geral=total_geral,
    )
    order.full_clean()
    order.save()
    return order


def bulk_create_order_items(order: Order, items: Iterable[dict]) -> list[OrderItem]:
    objs = [
        OrderItem(
            order_id=order,
            variant_id=item["variant"],
            order_item_quantity=item["quantity"],
            order_item_price=item["unit_price"],
        )
        for item in items
    ]
    for obj in objs:
        obj.full_clean()
    return OrderItem.objects.bulk_create(objs)


def update_order_status(order: Order, status: str) -> Order:
    order.order_status = status
    order.save(update_fields=["order_status", "updated_at"])
    return order