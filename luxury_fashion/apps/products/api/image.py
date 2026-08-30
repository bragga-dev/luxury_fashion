"""
ProductImage endpoints — galeria de imagens de um produto.

Duas rotas expostas neste módulo:
  - `nested_router`  → montado sob "/products/" (listar/enviar imagens de um produto)
  - `router`         → montado sob "/images/"    (operações sobre uma imagem específica)
"""
import uuid

from django_ratelimit.decorators import ratelimit
from ninja import File, Form, Router, UploadedFile

from luxury_fashion.apps.core.exceptions import ImageNotFound, InvalidImageFile, ProductNotFound
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.products.schemas.produc_image_schema import ImageOut, ImageUpdateIn
from luxury_fashion.apps.products.services.product_image_service import (
    delete_image_for_admin,
    get_image_for_all,
    list_images_queryset,
    reorder_image_for_admin,
    set_cover_image_for_admin,
    update_image_for_admin,
    upload_image_for_admin,
)

nested_router = Router()
router = Router()


# ── Nested sob /products/{product_id}/images ──────────────────────────────────

@nested_router.get(
    "/{product_id}/images",
    response={200: PageOut[ImageOut]},
    auth=None,
    summary="Lista as imagens de um produto (paginado)",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_images_router(
    request,
    product_id: uuid.UUID,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
):
    qs = list_images_queryset(product_id)
    return 200, paginate_queryset(qs, page, page_size, ImageOut.from_orm)


@nested_router.post(
    "/{product_id}/images",
    response={201: ImageOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Faz upload de uma nova imagem para o produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def upload_image_router(
    request,
    product_id: uuid.UUID,
    image: UploadedFile = File(...),
    is_cover: bool = Form(False),
    display_order: int = Form(0),
):
    try:
        created = upload_image_for_admin(
            product_id, image, is_cover=is_cover, display_order=display_order
        )
        return 201, created
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


# ── Standalone sob /images/{image_id} ──────────────────────────────────────────

@router.get(
    "/{image_id}",
    response={200: ImageOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de uma imagem",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_image_router(request, image_id: uuid.UUID):
    try:
        return 200, get_image_for_all(image_id)
    except ImageNotFound as e:
        return 404, {"detail": str(e)}


@router.patch(
    "/{image_id}",
    response={200: ImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza metadados de uma imagem (capa/ordem)",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_image_router(request, image_id: uuid.UUID, payload: ImageUpdateIn):
    try:
        return 200, update_image_for_admin(image_id, payload)
    except ImageNotFound as e:
        return 404, {"detail": str(e)}


@router.delete(
    "/{image_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma imagem",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_image_router(request, image_id: uuid.UUID):
    try:
        delete_image_for_admin(image_id)
        return 200, {"detail": "Imagem excluída com sucesso."}
    except ImageNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{image_id}/set-cover",
    response={200: ImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Define a imagem como capa do produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def set_cover_image_router(request, image_id: uuid.UUID):
    try:
        return 200, set_cover_image_for_admin(image_id)
    except ImageNotFound as e:
        return 404, {"detail": str(e)}


@router.patch(
    "/{image_id}/reorder",
    response={200: ImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Reordena uma imagem na galeria",
)
@ratelimit(key="user", rate="30/h", block=True)
def reorder_image_router(request, image_id: uuid.UUID, display_order: int):
    try:
        return 200, reorder_image_for_admin(image_id, display_order)
    except ImageNotFound as e:
        return 404, {"detail": str(e)}