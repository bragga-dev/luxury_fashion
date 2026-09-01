"""
CartItem Repository — persistência de CartItem.

Toda mutação de item recalcula os totais do Cart (`Cart.update_totals()`)
no fim — os totais não podem ficar dessincronizados esperando alguém
lembrar de chamar isso na camada de service.
"""
from typing import Optional

from luxury_fashion.apps.cart.models.cart_item_model import CartItem
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def add_item(cart: Cart, variant: ProductVariant, quantity: int = 1) -> CartItem:
    existing: Optional[CartItem] = CartItem.objects.filter(cart_id=cart, variant_id=variant).first()
    new_quantity = (existing.quantity_item if existing else 0) + quantity

    if new_quantity > variant.stock:
        raise ValueError("Estoque insuficiente para essa quantidade.")

    if existing:
        existing.quantity_item = new_quantity
        existing.save(update_fields=["quantity_item"])
        item = existing
    else:
        item = CartItem(cart_id=cart, variant_id=variant, quantity_item=quantity)
        item.save()

    cart.update_totals()
    return item


def update_item_quantity(item: CartItem, quantity: int) -> CartItem:
    if quantity > item.variant_id.stock:
        raise ValueError("Estoque insuficiente para essa quantidade.")
    item.quantity_item = quantity
    item.save(update_fields=["quantity_item"])
    item.cart_id.update_totals()
    return item


def remove_item(item: CartItem) -> None:
    cart = item.cart_id
    item.delete()
    cart.update_totals()


def clear_cart(cart: Cart) -> None:
    cart.items.all().delete()
    cart.update_totals()


def set_item_shipping(item: CartItem, shipping_type: str, shipping_value) -> CartItem:
    item.shipping_type = shipping_type
    item.shipping_value = shipping_value
    item.save(update_fields=["shipping_type", "shipping_value"])
    item.cart_id.update_totals()
    return item