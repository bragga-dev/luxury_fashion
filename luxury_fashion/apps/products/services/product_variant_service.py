"""
ProductVariant Services — orquestra regras de negócio de variantes de
produto (repositories + selectors), devolvendo sempre schemas prontos
para a camada de API.
"""
import uuid

from django.db import transaction
from django.db.models import ProtectedError

from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock
from luxury_fashion.apps.core.exceptions.products_exception import (
    ProductNotFound,
    VariantAlreadyExists,
    VariantInUse,
    VariantNotFound,
)
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant
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
    variant_exists_for_product_size_color,
    variant_exists_for_sku,
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
    return get_variants_by_product(product_id, active_only=active_only)


# ── Escrita ──────────────────────────────────────────────────────────────

def create_variant_for_admin(product_id: uuid.UUID, data: VariantCreateIn) -> VariantOut:
    product = get_product_by_id(product_id)
    if product is None:
        raise ProductNotFound()

    if data.sku and variant_exists_for_sku(sku=data.sku):
        raise VariantAlreadyExists("Já existe uma variante com esse SKU.")

    if variant_exists_for_product_size_color(
        product_id=product_id, size=data.size, color=data.color,
    ):
        raise VariantAlreadyExists()

    variant = create_variant(
        product_id=product,
        sku=data.sku,
        price=data.price,
        size=data.size,
        color=data.color,
        stock=data.stock,
    )
    return VariantOut.from_orm(variant)


def update_variant_for_admin(variant_id: uuid.UUID, data: VariantUpdateIn) -> VariantOut:
    variant = _get_variant_or_raise(variant_id=variant_id)
    fields = {
        key: value
        for key, value in data.dict(exclude_unset=True).items()
        if value is not None
    }

    if fields.get("sku") and variant_exists_for_sku(sku=fields["sku"], exclude_id=variant_id):
        raise VariantAlreadyExists("Já existe uma variante com esse SKU.")

    touches_combo = any(k in fields for k in ("size", "color"))
    if touches_combo:
        size = fields.get("size", variant.size)
        color = fields.get("color", variant.color)
        if variant_exists_for_product_size_color(
            product_id=variant.product_id_id, size=size, color=color, exclude_id=variant_id,
        ):
            raise VariantAlreadyExists()

    variant = update_variant(variant, **fields)
    return VariantOut.from_orm(variant)


def delete_variant_for_admin(variant_id: uuid.UUID) -> None:
    variant = _get_variant_or_raise(variant_id=variant_id)
    try:
        delete_variant(variant=variant)
    except ProtectedError:
        # Já vendida (OrderItem.variant_id é PROTECT): histórico fiscal não pode sumir.
        raise VariantInUse()


def activate_variant_for_admin(variant_id: uuid.UUID) -> VariantOut:
    variant = _get_variant_or_raise(variant_id=variant_id)
    variant = activate_variant(variant=variant)
    return VariantOut.from_orm(variant)


def deactivate_variant_for_admin(variant_id: uuid.UUID) -> VariantOut:
    variant = _get_variant_or_raise(variant_id=variant_id)
    variant = deactivate_variant(variant=variant)
    return VariantOut.from_orm(variant)


def _get_variant_locked_or_raise(variant_id: uuid.UUID):
    """
    Variante com a linha TRAVADA (select_for_update) — só chamar dentro de transaction.atomic.
    O estoque é lido e gravado aqui; sem o lock, uma confirmação de pagamento (que também trava a
    linha e debita) rodando ao mesmo tempo seria sobrescrita (lost update).
    """
    variant = ProductVariant.objects.select_for_update().select_related("product_id").filter(variant_id=variant_id).first()
    if variant is None:
        raise VariantNotFound()
    return variant


@transaction.atomic
def adjust_variant_stock_for_admin(variant_id: uuid.UUID, delta: int) -> VariantOut:
    variant = _get_variant_locked_or_raise(variant_id=variant_id)
    if variant.stock + delta < 0:
        raise InsufficientStock()
    variant = adjust_variant_stock(variant=variant, delta=delta)
    return VariantOut.from_orm(variant)


@transaction.atomic
def set_variant_stock_for_admin(variant_id: uuid.UUID, stock: int) -> VariantOut:
    if stock < 0:
        raise InsufficientStock()

    variant = _get_variant_locked_or_raise(variant_id=variant_id)
    variant = set_variant_stock(variant=variant, stock=stock)
    return VariantOut.from_orm(variant)