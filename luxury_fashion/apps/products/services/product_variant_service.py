"""
ProductVariant Services — orquestra regras de negócio de variantes de
produto (repositories + selectors), devolvendo sempre schemas prontos
para a camada de API.
"""
import uuid

from luxury_fashion.apps.core.exceptions.products_exception import (
    ProductNotFound,
    VariantAlreadyExists,
    VariantNotFound,
)
from luxury_fashion.apps.products.repositories.product_variant_repository import (
    activate_variant,
    adjust_variant_stock,
    create_variant,
    deactivate_variant,
    delete_variant,
    set_variant_stock,
    update_variant,
)
from luxury_fashion.apps.products.schemas.product_variant_schema import (
    VariantCreateIn,
    VariantOut,
    VariantUpdateIn,
)
from luxury_fashion.apps.products.selectors.product_selector import get_product_by_id
from luxury_fashion.apps.products.selectors.product_variant_selector import (
    get_variant_by_id,
    get_variants_by_product,
    variant_exists_for_product_size_color_gender,
)


def _get_variant_or_raise(variant_id: uuid.UUID):
    variant = get_variant_by_id(variant_id)
    if variant is None:
        raise VariantNotFound()
    return variant


# ── Leitura ──────────────────────────────────────────────────────────────

def get_variant_for_all(variant_id: uuid.UUID) -> VariantOut:
    variant = _get_variant_or_raise(variant_id)
    return VariantOut.from_orm(variant)


def list_variants_for_all(product_id: uuid.UUID, active_only: bool = True) -> list[VariantOut]:
    variants = get_variants_by_product(product_id, active_only=active_only)
    return [VariantOut.from_orm(variant) for variant in variants]


def list_variants_queryset(product_id: uuid.UUID, active_only: bool = True):
    """QuerySet bruto de variantes do produto, para paginação na camada de router."""
    return get_variants_by_product(product_id, active_only=active_only)


# ── Escrita ──────────────────────────────────────────────────────────────

def create_variant_for_admin(product_id: uuid.UUID, data: VariantCreateIn) -> VariantOut:
    product = get_product_by_id(product_id)
    if product is None:
        raise ProductNotFound()

    if variant_exists_for_product_size_color_gender(
        product_id=product_id, size=data.size, color=data.color, gender=data.gender,
    ):
        raise VariantAlreadyExists()

    variant = create_variant(
        product_id=product,
        price=data.price,
        size=data.size,
        color=data.color,
        gender=data.gender,
        stock=data.stock,
        description=data.description,
    )
    return VariantOut.from_orm(variant)


def update_variant_for_admin(variant_id: uuid.UUID, data: VariantUpdateIn) -> VariantOut:
    variant = _get_variant_or_raise(variant_id)
    fields = data.dict(exclude_unset=True)

    touches_combo = any(k in fields for k in ("size", "color", "gender"))
    if touches_combo:
        size = fields.get("size", variant.size)
        color = fields.get("color", variant.color)
        gender = fields.get("gender", variant.gender)
        if variant_exists_for_product_size_color_gender(
            product_id=variant.product_id_id, size=size, color=color, gender=gender, exclude_id=variant_id,
        ):
            raise VariantAlreadyExists()

    variant = update_variant(variant, **fields)
    return VariantOut.from_orm(variant)


def delete_variant_for_admin(variant_id: uuid.UUID) -> None:
    variant = _get_variant_or_raise(variant_id)
    delete_variant(variant)


def activate_variant_for_admin(variant_id: uuid.UUID) -> VariantOut:
    variant = _get_variant_or_raise(variant_id)
    variant = activate_variant(variant)
    return VariantOut.from_orm(variant)


def deactivate_variant_for_admin(variant_id: uuid.UUID) -> VariantOut:
    variant = _get_variant_or_raise(variant_id)
    variant = deactivate_variant(variant)
    return VariantOut.from_orm(variant)


def adjust_variant_stock_for_admin(variant_id: uuid.UUID, delta: int) -> VariantOut:
    """Ajusta o estoque em `delta` (positivo repõe, negativo baixa — ex.: venda)."""
    variant = _get_variant_or_raise(variant_id)
    variant = adjust_variant_stock(variant, delta)
    return VariantOut.from_orm(variant)


def set_variant_stock_for_admin(variant_id: uuid.UUID, stock: int) -> VariantOut:
    variant = _get_variant_or_raise(variant_id)
    variant = set_variant_stock(variant, stock)
    return VariantOut.from_orm(variant)