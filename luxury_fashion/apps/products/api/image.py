"""
Product image endpoints — CRUD da galeria de imagens de um produto.
Mesma situação da variant.py: services já existiam, faltava o router.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile

from luxury_fashion.apps.core.exceptions import ImageNotFound, InvalidImageFile, ProductNotFound
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.products.schemas.produc_image_schema import ImageOut, ImageUpdateIn
from luxury_fashion.apps.products.services.product_image_service import (
    delete_image_for_admin,
    list_images_for_all,
    reorder_image_for_admin,
    set_cover_image_for_admin,
    update_image_for_admin,
    upload_image_for_admin,
)

router = Router()


@router.get(
    "/{product_id}/images",
    response={200: list[ImageOut]},
    auth=AdminOnlyAuth(),
    summary="Lista as imagens de um produto (admin)",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_images_router(request, product_id: uuid.UUID):
    return 200, list_images_for_all(product_id)


@router.post(
    "/{product_id}/images",
    response={201: ImageOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Adiciona uma imagem à galeria do produto",
)
@ratelimit(key="user", rate="20/h", block=True)
def upload_image_router(
    request,
    product_id: uuid.UUID,
    image: UploadedFile = File(...),
    is_cover: bool = False,
    display_order: int = 0,
):
    try:
        return 201, upload_image_for_admin(product_id, image, is_cover, display_order)
    except ProductNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/images/{image_id}",
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
    "/images/{image_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma imagem do produto",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_image_router(request, image_id: uuid.UUID):
    try:
        delete_image_for_admin(image_id)
        return 200, {"detail": "Imagem excluída com sucesso."}
    except ImageNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/images/{image_id}/set-cover",
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


@router.post(
    "/images/{image_id}/reorder",
    response={200: ImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Reordena uma imagem do produto",
)
@ratelimit(key="user", rate="30/h", block=True)
def reorder_image_router(request, image_id: uuid.UUID, display_order: int):
    try:
        return 200, reorder_image_for_admin(image_id, display_order)
    except ImageNotFound as e:
        return 404, {"detail": str(e)}