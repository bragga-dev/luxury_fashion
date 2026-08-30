import uuid
from typing import List, Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.schemas.produc_image_schema import ImageOut
from luxury_fashion.apps.products.schemas.product_category_schema import ProductCategoryOut
from luxury_fashion.apps.products.schemas.product_shipping_schema import ShippingCreateIn
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantCreateIn, VariantOut


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


class ProductCreateFullIn(Schema):
    """
    Payload de conveniência para o formulário de cadastro completo: cria o
    produto, sua primeira variante (tamanho/cor/gênero/preço/estoque/descrição)
    e os dados de frete dessa variante (peso/dimensões) numa única chamada.

    As tabelas continuam normalizadas (Product / ProductVariant /
    ProductShipping) — este schema só agrupa a entrada para o front não
    precisar orquestrar 3 requisições.
    """
    product_name: str
    product_category_id: uuid.UUID
    variant: VariantCreateIn
    shipping: ShippingCreateIn

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
    category: ProductCategoryOut
    is_active: bool

    @classmethod
    def from_orm(cls, product: Product) -> "ProductListOut":
        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            category=ProductCategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
        )


class ProductOut(ProductListOut):
    """Versão completa — usada na página de detalhe (com variantes e imagens)."""
    variants: List[VariantOut]
    images: List[ImageOut] = []

    @classmethod
    def from_orm(cls, product: Product) -> "ProductOut":
        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            category=ProductCategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
            variants=[VariantOut.from_orm(v) for v in product.variants.filter(is_active=True)],
            images=[ImageOut.from_orm(img) for img in product.images.all()],
        )