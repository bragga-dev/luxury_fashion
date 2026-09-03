import uuid
from decimal import Decimal
from typing import List

from ninja import Schema

from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.cart.schemas.cart_item_schema import CartItemOut


class CartOut(Schema):
    cart_id: uuid.UUID
    items: List[CartItemOut]
    total_price: Decimal
    total_shipping: Decimal
    total_geral: Decimal

    @classmethod
    def from_orm(cls, cart: Cart) -> "CartOut":
        items = [CartItemOut.from_orm(item) for item in cart.items.all()]
        return cls(
            cart_id=cart.cart_id,
            items=items,
            total_price=cart.total_price,
            total_shipping=cart.total_shipping,
            total_geral=cart.total_geral,
        )