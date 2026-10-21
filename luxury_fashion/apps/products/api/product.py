"""
Product endpoints — vitrine/busca pública e CRUD administrativo.
"""
import uuid
from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import File, Form, Router, Status, UploadedFile
from pydantic import ValidationError as PydanticValidationError

from luxury_fashion.apps.core.exceptions import (
    CategoryNotFound,
    InvalidImageFile,
    ProductNameAlreadyExists,
    ProductNotFound,
    ShippingAlreadyExists,
    VariantAlreadyExists,
)
from luxury_fashion.apps.core.exceptions.products_exception import ProductInUse
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.products.schemas.product_enums_schema import (
    ProductColorEnum,
    ProductGenderEnum,
    ProductSizeEnum,
    ProductSortEnum,
)
from luxury_fashion.apps.products.schemas.product_schema import (
    ProductCreateFullIn,
    ProductCreateIn,
    ProductListOut,
    ProductOut,
    ProductUpdateIn,
)
from luxury_fashion.apps.products.services.product_service import (
    activate_product_for_admin,
    create_product_for_amdin,
    create_product_full_for_admin,
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
        "Suporta busca textual e filtros por categoria, gênero, tamanho, cor, estoque e faixa de preço (`min_price`/`max_price`; os critérios de tamanho/cor/estoque/preço valem para a MESMA variante). Ordenação (`sort`): recent, name, price_asc, price_desc, rating."
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
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    sort: Optional[ProductSortEnum] = None,
):
    qs = search_products_queryset(
        search=search,
        product_category_id=product_category_id,
        gender=gender.value if gender else None,
        size=size.value if size else None,
        color=color.value if color else None,
        in_stock_only=in_stock_only,
        active_only=True,
        sort=sort.value if sort else None,
        min_price=min_price,
        max_price=max_price,
    )
    return Status(200, paginate_queryset(qs, page, page_size, ProductListOut.from_orm))

@router.post(
    "/full",
    response={201: ProductOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria produto + 1ª variante + frete + imagens em uma única chamada",
    description=(
        "Endpoint de conveniência para o formulário de cadastro completo. "
        "É multipart/form-data (por causa das imagens):\n\n"
        "- `payload` (Form, string): JSON com `product_name`, `product_category_id`, "
        "`gender`, `description`, `variant` (tamanho/cor/preço/estoque) e `shipping` "
        "(peso/dimensões da embalagem) — mesmo formato do schema `ProductCreateFullIn`.\n"
        "- `images` (File, 0..N): quantas imagens forem necessárias para a galeria do produto.\n"
        "- `cover_index` (Form, int, default 0): posição (na lista `images`) que vira a "
        "imagem de capa. Se nenhuma imagem for enviada, o produto fica sem capa.\n\n"
        "Tudo é persistido atomicamente. As tabelas Product/ProductVariant/"
        "ProductShipping/ProductImage continuam separadas — isso só evita que o "
        "front precise fazer várias chamadas encadeadas. Para adicionar mais "
        "variantes ou imagens depois, use POST /products/{product_id}/variants "
        "e POST /products/{product_id}/images."
    ),
)
@ratelimit(key="user", rate="30/h", block=True)
def create_product_full_router(
    request,
    payload: str = Form(..., description="JSON no formato de ProductCreateFullIn"),
    images: List[UploadedFile] = File(None),
    cover_index: int = Form(0),
):
    try:
        data = ProductCreateFullIn.model_validate_json(payload)
    except PydanticValidationError as e:
        return Status(400, {"detail": str(e)})

    try:
        product = create_product_full_for_admin(data, images=images, cover_index=cover_index)
        return Status(201, product)
    except CategoryNotFound as e:
        return Status(404, {"detail": str(e)})
    except ProductNameAlreadyExists as e:
        return Status(409, {"detail": str(e)})
    except VariantAlreadyExists as e:
        return Status(409, {"detail": str(e)})
    except ShippingAlreadyExists as e:
        return Status(409, {"detail": str(e)})
    except InvalidImageFile as e:
        return Status(400, {"detail": str(e)})
    except DjangoValidationError as e:
        return Status(400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)})



@router.get(
    "/{product_id}",
    response={200: ProductOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de um produto (com variantes)",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_product_router(request, product_id: uuid.UUID):
    try:
        return Status(200, get_product_for_all(product_id))
    except ProductNotFound as e:
        return Status(404, {"detail": str(e)})


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
    return Status(200, paginate_queryset(qs, page, page_size, ProductListOut.from_orm))


# ── Escrita (admin) ───────────────────────────────────────────────────────────


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
        return Status(200, product)
    except ProductNotFound as e:
        return Status(404, {"detail": str(e)})
    except (CategoryNotFound, ProductNameAlreadyExists) as e:
        status = 404 if isinstance(e, CategoryNotFound) else 409
        return status, {"detail": str(e)}


@router.delete(
    "/{product_id}",
    response={200: MessageOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui um produto",
    description="Produto com variantes já vendidas não pode ser excluído (409) — desative-o.",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_product_router(request, product_id: uuid.UUID):
    try:
        delete_product_for_admin(product_id)
        return Status(200, {"detail": "Produto excluído com sucesso."})
    except ProductNotFound as e:
        return Status(404, {"detail": str(e)})
    except ProductInUse as e:
        return Status(409, {"detail": str(e)})


@router.post(
    "/{product_id}/activate",
    response={200: ProductOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa um produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def activate_product_router(request, product_id: uuid.UUID):
    try:
        return Status(200, activate_product_for_admin(product_id))
    except ProductNotFound as e:
        return Status(404, {"detail": str(e)})


@router.post(
    "/{product_id}/deactivate",
    response={200: ProductOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa um produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def deactivate_product_router(request, product_id: uuid.UUID):
    try:
        return Status(200, deactivate_product_for_admin(product_id))
    except ProductNotFound as e:
        return Status(404, {"detail": str(e)})