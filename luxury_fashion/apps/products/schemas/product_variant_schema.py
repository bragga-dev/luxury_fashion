import uuid
from decimal import Decimal
from typing import Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_variant_model import ProductVariant
from luxury_fashion.apps.products.schemas.product_enums_schema import (
    ProductColorEnum,
    ProductSizeEnum,
)


class VariantCreateIn(Schema):
    size: Optional[ProductSizeEnum] = None
    color: Optional[ProductColorEnum] = None
    price: Decimal
    stock: int = 0

    @field_validator("price")
    @classmethod
    def price_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Preço não pode ser negativo.")
        return v


class VariantUpdateIn(Schema):
    size: Optional[ProductSizeEnum] = None
    color: Optional[ProductColorEnum] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class VariantOut(Schema):
    variant_id: uuid.UUID
    size: Optional[str] = None
    color: Optional[str] = None
    price: Decimal
    stock: int
    is_active: bool
    in_stock: bool

    @classmethod
    def from_orm(cls, variant: ProductVariant) -> "VariantOut":
        return cls(
            variant_id=variant.variant_id,
            size=variant.size,
            color=variant.color,
            price=variant.price,
            stock=variant.stock,
            is_active=variant.is_active,
            in_stock=variant.in_stock,
        )