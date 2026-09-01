import re
import uuid
from decimal import Decimal
from typing import Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_shipping_model import ProductShipping


class ShippingCreateIn(Schema):
    weight: Decimal
    height: Decimal
    width: Decimal
    length: Decimal
    quantity: int = 1

    @field_validator("weight")
    @classmethod
    def weight_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("O peso deve ser maior que zero.")
        return v

    @field_validator("height", "width", "length")
    @classmethod
    def dimension_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("As dimensões devem ser maiores que zero.")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("A quantidade deve ser pelo menos 1.")
        return v


class ShippingUpdateIn(Schema):
    weight: Optional[Decimal] = None
    height: Optional[Decimal] = None
    width: Optional[Decimal] = None
    length: Optional[Decimal] = None
    quantity: Optional[int] = None

    @field_validator("weight")
    @classmethod
    def weight_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("O peso deve ser maior que zero.")
        return v

    @field_validator("height", "width", "length")
    @classmethod
    def dimension_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("As dimensões devem ser maiores que zero.")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_at_least_one(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("A quantidade deve ser pelo menos 1.")
        return v


class ShippingOut(Schema):
    product_shipping_id: uuid.UUID
    variant_id: uuid.UUID
    weight: Decimal
    height: Decimal
    width: Decimal
    length: Decimal
    quantity: int

    @classmethod
    def from_orm(cls, shipping: ProductShipping) -> "ShippingOut":
        return cls(
            product_shipping_id=shipping.product_shipping_id,
            variant_id=shipping.variant_id_id,
            weight=shipping.weight,
            height=shipping.height,
            width=shipping.width,
            length=shipping.length,
            quantity=shipping.quantity,
        )


# ── Cotação de frete (Frenet) ──────────────────────────────────────────────

class ShippingQuoteIn(Schema):
    """Payload de entrada pra cotar o frete de uma variante na Frenet."""

    recipient_cep: str
    quantity: Optional[int] = None

    @field_validator("recipient_cep")
    @classmethod
    def recipient_cep_format(cls, v: str) -> str:
        cep = re.sub(r"\D", "", v)
        if len(cep) != 8:
            raise ValueError("O CEP de destino deve possuir 8 dígitos.")
        return cep

    @field_validator("quantity")
    @classmethod
    def quantity_at_least_one(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("A quantidade deve ser pelo menos 1.")
        return v


class FrenetShippingOptionOut(Schema):
    """Uma opção de frete retornada pela Frenet (uma transportadora/serviço)."""

    carrier: str
    service: str
    service_code: Optional[str] = None
    price: Decimal
    delivery_time_days: int
    error: bool = False
    error_message: Optional[str] = None