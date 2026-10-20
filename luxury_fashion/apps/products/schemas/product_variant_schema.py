import uuid
from decimal import Decimal
from typing import Optional

from ninja import Schema
from pydantic import Field, field_validator

from luxury_fashion.apps.products.models.product_variant_model import ProductVariant
from luxury_fashion.apps.products.schemas.product_enums_schema import (
    ProductColorEnum,
    ProductSizeEnum,
)


class VariantCreateIn(Schema):
    sku: Optional[str] = Field(default=None, max_length=50)
    size: Optional[ProductSizeEnum] = None
    color: Optional[ProductColorEnum] = None
    price: Decimal
    stock: int = 0

    @field_validator("sku")
    @classmethod
    def sku_normalize(cls, v: Optional[str]) -> Optional[str]:
        # "" vira None: o campo é único, e vários "" colidiriam entre si.
        if v is None:
            return None
        return v.strip() or None

    @field_validator("price")
    @classmethod
    def price_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Preço não pode ser negativo.")
        return v


class VariantUpdateIn(Schema):
    sku: Optional[str] = Field(default=None, max_length=50)
    size: Optional[ProductSizeEnum] = None
    color: Optional[ProductColorEnum] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("sku")
    @classmethod
    def sku_normalize(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip() or None


class VariantOut(Schema):
    variant_id: uuid.UUID
    sku: Optional[str] = None
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
            sku=variant.sku,
            size=variant.size,
            color=variant.color,
            price=variant.price,
            stock=variant.stock,
            is_active=variant.is_active,
            in_stock=variant.in_stock,
        )


def _cover_image_url(product) -> Optional[str]:
    """
    URL da capa do produto: a imagem marcada como capa; na falta, a primeira por display_order.
    Usa `product.images.all()` — aproveita o prefetch dos selectors (carrinho/pedidos), sem query extra.
    """
    images = list(product.images.all())
    if not images:
        return None
    cover = next((img for img in images if img.is_cover), images[0])
    try:
        return cover.product_image.url
    except Exception:
        return None


class VariantWithProductOut(VariantOut):
    """
    Variante + dados do produto dono. Usada nos itens de carrinho e de pedido, onde o front precisa
    mostrar o nome, a miniatura e o link do produto sem uma chamada extra por item.
    """
    product_id: uuid.UUID
    product_name: str
    cover_image_url: Optional[str] = None

    @classmethod
    def from_orm(cls, variant: ProductVariant) -> "VariantWithProductOut":
        product = variant.product_id
        return cls(
            variant_id=variant.variant_id,
            sku=variant.sku,
            size=variant.size,
            color=variant.color,
            price=variant.price,
            stock=variant.stock,
            is_active=variant.is_active,
            in_stock=variant.in_stock,
            product_id=product.product_id,
            product_name=product.product_name,
            cover_image_url=_cover_image_url(product),
        )