import uuid
from typing import List, Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.schemas.product_category_schema import CategoryOut
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantOut


class ProductCreateIn(Schema):
    product_name: str
    product_category_id: uuid.UUID

    @field_validator("product_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v


class ProductUpdateIn(Schema):
    product_name: Optional[str] = None
    product_category_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class ProductListOut(Schema):
    """Versão enxuta — usada na vitrine/listagem, sem carregar as variantes."""
    product_id: uuid.UUID
    product_name: str
    category: CategoryOut
    is_active: bool

    @classmethod
    def from_orm(cls, product: Product) -> "ProductListOut":
        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            category=CategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
        )


class ProductOut(ProductListOut):
    """Versão completa — usada na página de detalhe (com variantes)."""
    variants: List[VariantOut]

    @classmethod
    def from_orm(cls, product: Product) -> "ProductOut":
        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            category=CategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
            variants=[VariantOut.from_orm(v) for v in product.variants.filter(is_active=True)],
        )


