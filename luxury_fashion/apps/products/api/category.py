"""
Category endpoints — CRUD de categorias de produto.
"""
import uuid
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile

from luxury_fashion.apps.core.exceptions import (
    CategoryHasProducts,
    CategoryNameAlreadyExists,
    CategoryNotFound,
    InvalidImageFile,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.products.schemas.product_category_schema import (
    ProductCategoryCreateIn,
    ProductCategoryOut,
    ProductCategoryUpdateIn,
)
from luxury_fashion.apps.products.services.product_category_service import (
    activate_category_for_admin,
    create_category_for_admin,
    deactivate_category_for_admin,
    delete_category_for_admin,
    get_category_for_all,
    list_categories_queryset,
    remove_category_image_for_admin,
    update_category_for_admin,
    upload_category_image_for_admin,
)

router = Router()


# ── Listagem / Detalhe (público) ──────────────────────────────────────────────

@router.get(
    "",
    response={200: PageOut[ProductCategoryOut]},
    auth=None,
    summary="Lista categorias de produto (paginado)",
    description="Retorna as categorias ativas, paginadas. Uso público (vitrine/menu).",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_categories_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    active_only: bool = True,
):
    qs = list_categories_queryset(active_only=active_only)
    return 200, paginate_queryset(qs, page, page_size, ProductCategoryOut.from_orm)


@router.get(
    "/{category_id}",
    response={200: ProductCategoryOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de uma categoria",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_category_router(request, category_id: uuid.UUID):
    try:
        return 200, get_category_for_all(category_id)
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}


# ── Escrita (admin) ───────────────────────────────────────────────────────────

@router.post(
    "",
    response={201: ProductCategoryOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria uma nova categoria",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_category_router(request, payload: ProductCategoryCreateIn):
    try:
        category = create_category_for_admin(payload)
        return 201, category
    except CategoryNameAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/{category_id}",
    response={200: ProductCategoryOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza uma categoria existente",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_category_router(request, category_id: uuid.UUID, payload: ProductCategoryUpdateIn):
    try:
        category = update_category_for_admin(category_id, payload)
        return 200, category
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}
    except CategoryNameAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.delete(
    "/{category_id}",
    response={200: MessageOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma categoria",
    description="Não é possível excluir uma categoria que ainda possua produtos vinculados.",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_category_router(request, category_id: uuid.UUID):
    try:
        delete_category_for_admin(category_id)
        return 200, {"detail": "Categoria excluída com sucesso."}
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}
    except CategoryHasProducts as e:
        return 409, {"detail": str(e)}


@router.post(
    "/{category_id}/activate",
    response={200: ProductCategoryOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa uma categoria",
)
@ratelimit(key="user", rate="30/h", block=True)
def activate_category_router(request, category_id: uuid.UUID):
    try:
        return 200, activate_category_for_admin(category_id)
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{category_id}/deactivate",
    response={200: ProductCategoryOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa uma categoria",
)
@ratelimit(key="user", rate="30/h", block=True)
def deactivate_category_router(request, category_id: uuid.UUID):
    try:
        return 200, deactivate_category_for_admin(category_id)
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}


# ── Imagem (admin) ────────────────────────────────────────────────────────────

@router.post(
    "/{category_id}/image",
    response={200: ProductCategoryOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Faz upload/troca a imagem da categoria",
)
@ratelimit(key="user", rate="20/h", block=True)
def upload_category_image_router(request, category_id: uuid.UUID, image: UploadedFile = File(...)):
    try:
        return 200, upload_category_image_for_admin(category_id, image)
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{category_id}/image",
    response={200: ProductCategoryOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Remove a imagem da categoria (volta para a imagem padrão)",
)
@ratelimit(key="user", rate="20/h", block=True)
def remove_category_image_router(request, category_id: uuid.UUID):
    try:
        return 200, remove_category_image_for_admin(category_id)
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}