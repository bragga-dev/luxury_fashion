import uuid
from decimal import Decimal

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.cart.models.cart_item_model import CartItem
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantWithProductOut


class CartItemCreateIn(Schema):
    variant_id: uuid.UUID
    quantity_item: int = 1

    @field_validator("quantity_item")
    @classmethod
    def quantity_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantidade deve ser no mínimo 1.")
        return v


class CartItemUpdateIn(Schema):
    quantity_item: int

    @field_validator("quantity_item")
    @classmethod
    def quantity_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantidade deve ser no mínimo 1.")
        return v


class CartItemOut(Schema):
    cart_item_id: uuid.UUID
    variant: VariantWithProductOut
    quantity_item: int
    unit_price_item: Decimal
    subtotal: Decimal

    @classmethod
    def from_orm(cls, item: CartItem) -> "CartItemOut":
        return cls(
            cart_item_id=item.cart_item_id,
            variant=VariantWithProductOut.from_orm(item.variant_id),
            quantity_item=item.quantity_item,
            unit_price_item=item.unit_price_item,
            subtotal=item.subtotal(),
        )