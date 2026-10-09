"""
Variant endpoints — CRUD de variantes (tamanho/cor/gênero/preço/estoque)
de um produto. Os services já existiam (product_variant_service.py); só
faltava expor via router, então o front não tinha como adicionar/editar
variantes depois da criação do produto (só o POST /products/full cobria
a primeira variante).
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from luxury_fashion.apps.core.exceptions import (
    ProductNotFound,
    ShippingAlreadyExists,
    ShippingNotFound,
    VariantAlreadyExists,
    VariantNotFound,
)
from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.products.schemas.product_shipping_schema import (
    ShippingCreateIn,
    ShippingOut,
    ShippingUpdateIn,
)
from luxury_fashion.apps.products.schemas.product_variant_schema import (
    VariantCreateIn,
    VariantOut,
    VariantUpdateIn,
)
from luxury_fashion.apps.products.services.product_shipping_service import (
    create_shipping_for_admin,
    get_shipping_for_all,
    update_shipping_for_admin,
)
from luxury_fashion.apps.products.services.product_variant_service import (
    activate_variant_for_admin,
    create_variant_for_admin,
    deactivate_variant_for_admin,
    delete_variant_for_admin,
    list_variants_for_all,
    set_variant_stock_for_admin,
    update_variant_for_admin,
)

router = Router()


# ── Leitura (admin) ────────────────────────────────────────────────────────────

@router.get(
    "/{product_id}/variants",
    response={200: list[VariantOut]},
    auth=AdminOnlyAuth(),
    summary="Lista as variantes de um produto (admin — inclui inativas)",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_variants_router(request, product_id: uuid.UUID, active_only: bool = False):
    return 200, list_variants_for_all(product_id, active_only=active_only)


# ── Escrita (admin) ────────────────────────────────────────────────────────────

@router.post(
    "/{product_id}/variants",
    response={201: VariantOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Adiciona uma nova variante ao produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_variant_router(request, product_id: uuid.UUID, payload: VariantCreateIn):
    try:
        return 201, create_variant_for_admin(product_id, payload)
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except VariantAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/variants/{variant_id}",
    response={200: VariantOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza uma variante existente",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_variant_router(request, variant_id: uuid.UUID, payload: VariantUpdateIn):
    try:
        return 200, update_variant_for_admin(variant_id, payload)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except VariantAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.delete(
    "/variants/{variant_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma variante",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_variant_router(request, variant_id: uuid.UUID):
    try:
        delete_variant_for_admin(variant_id)
        return 200, {"detail": "Variante excluída com sucesso."}
    except VariantNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/variants/{variant_id}/activate",
    response={200: VariantOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa uma variante",
)
@ratelimit(key="user", rate="30/h", block=True)
def activate_variant_router(request, variant_id: uuid.UUID):
    try:
        return 200, activate_variant_for_admin(variant_id)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/variants/{variant_id}/deactivate",
    response={200: VariantOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa uma variante",
)
@ratelimit(key="user", rate="30/h", block=True)
def deactivate_variant_router(request, variant_id: uuid.UUID):
    try:
        return 200, deactivate_variant_for_admin(variant_id)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/variants/{variant_id}/stock",
    response={200: VariantOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Define o estoque absoluto de uma variante",
)
@ratelimit(key="user", rate="60/h", block=True)
def set_variant_stock_router(request, variant_id: uuid.UUID, stock: int):
    try:
        return 200, set_variant_stock_for_admin(variant_id, stock)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except InsufficientStock as e:
        return 409, {"detail": str(e)}


# ── Embalagem / dados de frete da variante (admin) ─────────────────────────────

@router.get(
    "/variants/{variant_id}/shipping",
    response={200: ShippingOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Consulta os dados de embalagem/frete (peso e dimensões) de uma variante",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_variant_shipping_router(request, variant_id: uuid.UUID):
    try:
        return 200, get_shipping_for_all(variant_id)
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/variants/{variant_id}/shipping",
    response={201: ShippingOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cadastra os dados de embalagem/frete de uma variante que ainda não tem",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_variant_shipping_router(request, variant_id: uuid.UUID, payload: ShippingCreateIn):
    try:
        return 201, create_shipping_for_admin(variant_id, payload)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except ShippingAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/variants/{variant_id}/shipping",
    response={200: ShippingOut, 404: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza a embalagem/frete (peso, altura, largura, comprimento, quantidade) de uma variante",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_variant_shipping_router(request, variant_id: uuid.UUID, payload: ShippingUpdateIn):
    try:
        return 200, update_shipping_for_admin(variant_id, payload)
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}