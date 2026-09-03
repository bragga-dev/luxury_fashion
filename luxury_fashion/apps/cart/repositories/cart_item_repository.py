"""
CartItem Repository — persistência pura de CartItem. Nenhuma regra de
negócio aqui (validação de estoque, decisão de criar vs. incrementar,
etc.) — isso é responsabilidade exclusiva do service. O repository só
executa a operação de persistência que já foi decidida e validada antes.

Toda mutação recalcula os totais do Cart (`Cart.update_totals()`) no fim
— consistência do agregado Cart/CartItem, não regra de negócio.
"""
from luxury_fashion.apps.cart.models.cart_item_model import CartItem
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def create_item(cart: Cart, variant: ProductVariant, quantity: int = 1) -> CartItem:
    item = CartItem(cart_id=cart, variant_id=variant, quantity_item=quantity)
    item.save()
    cart.update_totals()
    return item


def increment_item_quantity(item: CartItem, quantity: int) -> CartItem:
    """Soma `quantity` à quantidade já existente do item."""
    item.quantity_item += quantity
    item.save(update_fields=["quantity_item"])
    item.cart_id.update_totals()
    return item


def update_item_quantity(item: CartItem, quantity: int) -> CartItem:
    """Define a quantidade exata (não soma)."""
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