"""
Variant endpoints — variantes (tamanho/cor/gênero/preço/estoque) de um produto.

Duas rotas expostas neste módulo:
  - `nested_router`  → montado sob "/products/" (listar/criar variantes de um produto)
  - `router`         → montado sob "/variants/"  (operações sobre uma variante específica)
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema

from luxury_fashion.apps.core.exceptions import (
    ProductNotFound,
    VariantAlreadyExists,
    VariantNotFound,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.products.schemas.product_variant_schema import (
    VariantCreateIn,
    VariantOut,
    VariantUpdateIn,
)
from luxury_fashion.apps.products.services.product_variant_service import (
    activate_variant_for_admin,
    adjust_variant_stock_for_admin,
    create_variant_for_admin,
    deactivate_variant_for_admin,
    delete_variant_for_admin,
    get_variant_for_all,
    list_variants_queryset,
    set_variant_stock_for_admin,
    update_variant_for_admin,
)

nested_router = Router()
router = Router()


class StockAdjustIn(Schema):
    delta: int


class StockSetIn(Schema):
    stock: int


# ── Nested sob /products/{product_id}/variants ───────────────────────────────

@nested_router.get(
    "/{product_id}/variants",
    response={200: PageOut[VariantOut]},
    auth=None,
    summary="Lista as variantes de um produto (paginado)",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_variants_router(
    request,
    product_id: uuid.UUID,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    active_only: bool = True,
):
    qs = list_variants_queryset(product_id, active_only=active_only)
    return 200, paginate_queryset(qs, page, page_size, VariantOut.from_orm)


@nested_router.post(
    "/{product_id}/variants",
    response={201: VariantOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria uma nova variante para o produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_variant_router(request, product_id: uuid.UUID, payload: VariantCreateIn):
    try:
        variant = create_variant_for_admin(product_id, payload)
        return 201, variant
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except VariantAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


# ── Standalone sob /variants/{variant_id} ─────────────────────────────────────

@router.get(
    "/{variant_id}",
    response={200: VariantOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de uma variante",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_variant_router(request, variant_id: uuid.UUID):
    try:
        return 200, get_variant_for_all(variant_id)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}


@router.patch(
    "/{variant_id}",
    response={200: VariantOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza uma variante existente",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_variant_router(request, variant_id: uuid.UUID, payload: VariantUpdateIn):
    try:
        variant = update_variant_for_admin(variant_id, payload)
        return 200, variant
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except VariantAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.delete(
    "/{variant_id}",
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
    "/{variant_id}/activate",
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
    "/{variant_id}/deactivate",
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


# ── Estoque ────────────────────────────────────────────────────────────────

@router.post(
    "/{variant_id}/stock/adjust",
    response={200: VariantOut, 404: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ajusta o estoque da variante (delta)",
    description="Delta positivo repõe estoque; delta negativo baixa (ex.: venda manual).",
)
@ratelimit(key="user", rate="60/h", block=True)
def adjust_variant_stock_router(request, variant_id: uuid.UUID, payload: StockAdjustIn):
    try:
        return 200, adjust_variant_stock_for_admin(variant_id, payload.delta)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except ValueError as e:
        return 400, {"detail": str(e)}


@router.put(
    "/{variant_id}/stock",
    response={200: VariantOut, 404: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Define o estoque absoluto da variante",
)
@ratelimit(key="user", rate="60/h", block=True)
def set_variant_stock_router(request, variant_id: uuid.UUID, payload: StockSetIn):
    try:
        return 200, set_variant_stock_for_admin(variant_id, payload.stock)
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}