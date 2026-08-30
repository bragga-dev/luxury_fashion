"""
ProductShipping endpoints — dados físicos (peso/dimensões) de uma variante,
usados na cotação de frete.

Montado sob "/variants/{variant_id}/shipping".
"""
import uuid
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from luxury_fashion.apps.core.exceptions import (
    ShippingAlreadyExists,
    ShippingNotFound,
    VariantNotFound,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.products.schemas.product_shipping_schema import (
    ShippingCreateIn,
    ShippingOut,
    ShippingUpdateIn,
)
from luxury_fashion.apps.products.services.product_shipping_service import (
    create_shipping_for_admin,
    delete_shipping_for_admin,
    get_shipping_for_all,
    get_shipping_payload,
    update_shipping_for_admin,
)

router = Router()


# ── Cotação (público — usado no PDP/carrinho, inclusive por visitantes) ───────

@router.get(
    "/{variant_id}/shipping/quote",
    response={200: dict, 404: MessageOut},
    auth=None,
    summary="Monta o payload de cotação de frete para a variante",
    description=(
        "Retorna peso/dimensões prontos para a API de frete (ex.: Melhor Envio). "
        "`quantity` sobrescreve a quantidade padrão de embalagem cadastrada."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def get_shipping_quote_router(request, variant_id: uuid.UUID, quantity: Optional[int] = None):
    try:
        return 200, get_shipping_payload(variant_id, quantity=quantity)
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}


# ── CRUD (admin) ───────────────────────────────────────────────────────────────

@router.get(
    "/{variant_id}/shipping",
    response={200: ShippingOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Detalhe dos dados de frete de uma variante",
)
@ratelimit(key="user", rate="60/m", block=True)
def detail_shipping_router(request, variant_id: uuid.UUID):
    try:
        return 200, get_shipping_for_all(variant_id)
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{variant_id}/shipping",
    response={201: ShippingOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cadastra os dados de frete de uma variante",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_shipping_router(request, variant_id: uuid.UUID, payload: ShippingCreateIn):
    try:
        shipping = create_shipping_for_admin(variant_id, payload)
        return 201, shipping
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except ShippingAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/{variant_id}/shipping",
    response={200: ShippingOut, 404: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza os dados de frete de uma variante",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_shipping_router(request, variant_id: uuid.UUID, payload: ShippingUpdateIn):
    try:
        shipping = update_shipping_for_admin(variant_id, payload)
        return 200, shipping
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.delete(
    "/{variant_id}/shipping",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui os dados de frete de uma variante",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_shipping_router(request, variant_id: uuid.UUID):
    try:
        delete_shipping_for_admin(variant_id)
        return 200, {"detail": "Dados de frete excluídos com sucesso."}
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}