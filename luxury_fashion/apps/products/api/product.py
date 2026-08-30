"""
Product endpoints — vitrine/busca pública e CRUD administrativo.
"""
import uuid
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from luxury_fashion.apps.core.exceptions import (
    CategoryNotFound,
    ProductNameAlreadyExists,
    ProductNotFound,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.products.schemas.product_enums_schema import (
    ProductColorEnum,
    ProductGenderEnum,
    ProductSizeEnum,
)
from luxury_fashion.apps.products.schemas.product_schema import (
    ProductCreateIn,
    ProductListOut,
    ProductOut,
    ProductUpdateIn,
)
from luxury_fashion.apps.products.services.product_service import (
    activate_product_for_admin,
    create_product_for_amdin,
    deactivate_product_for_admin,
    delete_product_for_admin,
    get_product_for_all,
    search_products_queryset,
    update_product_for_admin,
)

router = Router()


# ── Vitrine / Busca (público) ─────────────────────────────────────────────────

@router.get(
    "",
    response={200: PageOut[ProductListOut]},
    auth=None,
    summary="Lista/busca produtos na vitrine (paginado)",
    description=(
        "Endpoint público da vitrine. Sempre retorna apenas produtos ativos. "
        "Suporta busca textual e filtros por categoria, gênero, tamanho, cor e estoque."
    ),
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_products_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[ProductGenderEnum] = None,
    size: Optional[ProductSizeEnum] = None,
    color: Optional[ProductColorEnum] = None,
    in_stock_only: bool = False,
):
    qs = search_products_queryset(
        search=search,
        product_category_id=product_category_id,
        gender=gender.value if gender else None,
        size=size.value if size else None,
        color=color.value if color else None,
        in_stock_only=in_stock_only,
        active_only=True,
    )
    return 200, paginate_queryset(qs, page, page_size, ProductListOut.from_orm)


@router.get(
    "/{product_id}",
    response={200: ProductOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de um produto (com variantes)",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_product_router(request, product_id: uuid.UUID):
    try:
        return 200, get_product_for_all(product_id)
    except ProductNotFound as e:
        return 404, {"detail": str(e)}


# ── Painel administrativo ─────────────────────────────────────────────────────

@router.get(
    "/admin/list",
    response={200: PageOut[ProductListOut]},
    auth=AdminOnlyAuth(),
    summary="Lista/busca produtos (admin — inclui inativos, paginado)",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_products_admin_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[ProductGenderEnum] = None,
    size: Optional[ProductSizeEnum] = None,
    color: Optional[ProductColorEnum] = None,
    in_stock_only: bool = False,
    active_only: bool = False,
):
    qs = search_products_queryset(
        search=search,
        product_category_id=product_category_id,
        gender=gender.value if gender else None,
        size=size.value if size else None,
        color=color.value if color else None,
        in_stock_only=in_stock_only,
        active_only=active_only,
    )
    return 200, paginate_queryset(qs, page, page_size, ProductListOut.from_orm)


# ── Escrita (admin) ───────────────────────────────────────────────────────────

@router.post(
    "",
    response={201: ProductOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria um novo produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_product_router(request, payload: ProductCreateIn):
    try:
        product = create_product_for_amdin(payload)
        return 201, product
    except CategoryNotFound as e:
        return 404, {"detail": str(e)}
    except ProductNameAlreadyExists as e:
        return 409, {"detail": str(e)}


@router.patch(
    "/{product_id}",
    response={200: ProductOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza um produto existente",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_product_router(request, product_id: uuid.UUID, payload: ProductUpdateIn):
    try:
        product = update_product_for_admin(product_id, payload)
        return 200, product
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except (CategoryNotFound, ProductNameAlreadyExists) as e:
        status = 404 if isinstance(e, CategoryNotFound) else 409
        return status, {"detail": str(e)}


@router.delete(
    "/{product_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui um produto",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_product_router(request, product_id: uuid.UUID):
    try:
        delete_product_for_admin(product_id)
        return 200, {"detail": "Produto excluído com sucesso."}
    except ProductNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{product_id}/activate",
    response={200: ProductOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa um produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def activate_product_router(request, product_id: uuid.UUID):
    try:
        return 200, activate_product_for_admin(product_id)
    except ProductNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{product_id}/deactivate",
    response={200: ProductOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa um produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def deactivate_product_router(request, product_id: uuid.UUID):
    try:
        return 200, deactivate_product_for_admin(product_id)
    except ProductNotFound as e:
        return 404, {"detail": str(e)}