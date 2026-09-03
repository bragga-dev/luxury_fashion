"""
ProductShipping Services — orquestra os dados físicos (peso/dimensões) de
uma variante usados na cotação de frete.
"""
import uuid
from typing import Optional

from luxury_fashion.apps.core.exceptions.products_exception import (
    ShippingAlreadyExists,
    ShippingNotFound,
    VariantNotFound,
)
from luxury_fashion.apps.products.repositories.product_shipping_repository import (
    create_shipping,
    delete_shipping,
    update_shipping,
)
from luxury_fashion.apps.products.schemas.product_shipping_schema import (
    ShippingCreateIn,
    ShippingOut,
    ShippingUpdateIn,
)
from luxury_fashion.apps.products.selectors.product_shipping_selector import (
    get_shipping_by_variant,
    shipping_exists_for_variant,
)
from luxury_fashion.apps.products.selectors.product_variant_selector import get_variant_by_id


def _get_shipping_or_raise(variant_id: uuid.UUID):
    shipping = get_shipping_by_variant(variant_id)
    if shipping is None:
        raise ShippingNotFound()
    return shipping


# ── Leitura ──────────────────────────────────────────────────────────────

def get_shipping_for_all(variant_id: uuid.UUID) -> ShippingOut:
    shipping = _get_shipping_or_raise(variant_id)
    return ShippingOut.from_orm(shipping)


def get_shipping_payload(variant_id: uuid.UUID, quantity: Optional[int] = None) -> dict:
    """
    Monta o payload pronto para a API de frete (ex.: Melhor Envio) a
    partir dos dados cadastrados da variante.

    `quantity` sobrescreve a quantidade padrão de embalagem quando o
    chamador já sabe quantas unidades vão no carrinho/pedido — é isso
    que deve ser usado no checkout, não o valor default do cadastro.
    """
    shipping = _get_shipping_or_raise(variant_id)
    payload = shipping.to_shipping_payload()
    if quantity is not None:
        payload["quantity"] = quantity
    return payload


# ── Escrita ──────────────────────────────────────────────────────────────

def create_shipping_for_admin(variant_id: uuid.UUID, data: ShippingCreateIn) -> ShippingOut:
    variant = get_variant_by_id(variant_id)
    if variant is None:
        raise VariantNotFound()

    if shipping_exists_for_variant(variant_id):
        raise ShippingAlreadyExists()

    shipping = create_shipping(
        variant_id=variant,
        weight=data.weight,
        height=data.height,
        width=data.width,
        length=data.length,
        quantity=data.quantity,
    )
    return ShippingOut.from_orm(shipping)


def update_shipping_for_admin(variant_id: uuid.UUID, data: ShippingUpdateIn) -> ShippingOut:
    shipping = _get_shipping_or_raise(variant_id)
    shipping = update_shipping(shipping, **data.dict(exclude_unset=True))
    return ShippingOut.from_orm(shipping)


def delete_shipping_for_admin(variant_id: uuid.UUID) -> None:
    shipping = _get_shipping_or_raise(variant_id)
    delete_shipping(shipping)