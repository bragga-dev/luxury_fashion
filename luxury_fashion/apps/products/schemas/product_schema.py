import uuid
from decimal import Decimal
from typing import List, Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.schemas.product_enums_schema import ProductGenderEnum
from luxury_fashion.apps.products.schemas.produc_image_schema import ImageOut
from luxury_fashion.apps.products.schemas.product_category_schema import ProductCategoryOut
from luxury_fashion.apps.products.schemas.product_shipping_schema import ShippingCreateIn
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantCreateIn, VariantOut


def _pick_cover_image(images: list) -> Optional["ImageOut"]:
    """Capa explícita (`is_cover=True`); na ausência, a primeira por display_order."""
    if not images:
        return None
    cover = next((img for img in images if img.is_cover), None)
    return ImageOut.from_orm(cover or images[0])


def _rating_fields(product: Product) -> dict:
    """Lê as anotações `avg_rating`/`total_reviews` do selector (ausentes em objetos não anotados)."""
    avg = getattr(product, "avg_rating", None)
    return {
        "average_rating": round(Decimal(str(avg)), 1) if avg is not None else Decimal("0.0"),
        "total_reviews": getattr(product, "total_reviews", None) or 0,
    }


class ProductCreateIn(Schema):
    product_name: str
    product_category_id: uuid.UUID
    gender: ProductGenderEnum
    description: str = ""

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
    produto (nome/categoria/gênero/descrição), sua primeira variante
    (tamanho/cor/preço/estoque) e os dados de frete dessa variante
    (peso/dimensões) numa única chamada.

    As tabelas continuam normalizadas (Product / ProductVariant /
    ProductShipping) — este schema só agrupa a entrada para o front não
    precisar orquestrar 3 requisições.
    """
    product_name: str
    product_category_id: uuid.UUID
    gender: ProductGenderEnum
    description: str = ""
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
    gender: Optional[ProductGenderEnum] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductListOut(Schema):
    """
    Versão da vitrine/listagem: inclui as variantes ativas (preço, tamanho,
    cor, estoque etc.), a imagem de capa e um resumo agregado (faixa de
    preço e disponibilidade) pra evitar o front varrer `variants` na mão.
    Não carrega a galeria completa — para isso use o endpoint de detalhe
    (`ProductOut`).
    """
    product_id: uuid.UUID
    product_name: str
    gender: str
    description: str
    category: ProductCategoryOut
    is_active: bool
    variants: List[VariantOut]
    cover_image: Optional[ImageOut] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock: bool = False
    average_rating: Decimal = Decimal("0.0")  # só avaliações autorizadas; 0.0 = sem avaliações
    total_reviews: int = 0

    @classmethod
    def from_orm(cls, product: Product) -> "ProductListOut":
        # `product.variants`/`product.images` já vêm prefetchadas
        # (variants filtradas por is_active=True, images ordenadas com a
        # capa primeiro) pelo selector — usar `.all()` aproveita o cache
        # do prefetch em vez de disparar uma query nova por produto.
        images = list(product.images.all())
        variants = [VariantOut.from_orm(v) for v in product.variants.all()]
        prices = [v.price for v in variants]

        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            gender=product.gender,
            description=product.description,
            category=ProductCategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
            variants=variants,
            cover_image=_pick_cover_image(images),
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            in_stock=any(v.in_stock for v in variants),
            **_rating_fields(product),
        )


class ProductOut(ProductListOut):
    """Versão completa — usada na página de detalhe (com variantes e imagens)."""
    variants: List[VariantOut]
    images: List[ImageOut] = []
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, product: Product) -> "ProductOut":
        images = list(product.images.all())
        variants = [VariantOut.from_orm(v) for v in product.variants.filter(is_active=True)]
        prices = [v.price for v in variants]

        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            gender=product.gender,
            description=product.description,
            category=ProductCategoryOut.from_orm(product.product_category_id),
            is_active=product.is_active,
            variants=variants,
            images=[ImageOut.from_orm(img) for img in images],
            cover_image=_pick_cover_image(images),
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            in_stock=any(v.in_stock for v in variants),
            **_rating_fields(product),
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat(),
        )