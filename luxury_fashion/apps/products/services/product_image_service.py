"""
ProductImage Services — orquestra regras de negócio de imagens de
produto (repositories + selectors), devolvendo sempre schemas prontos
para a camada de API.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import UploadedFile

from luxury_fashion.apps.core.exceptions.media import InvalidImageFile
from luxury_fashion.apps.core.exceptions.products_exception import ImageNotFound, ProductNotFound
from luxury_fashion.apps.core.validators.image_validator import validate_image_file
from luxury_fashion.apps.products.repositories.product_image_repository import (
    create_image, 
    delete_image, 
    reorder_image, 
    set_cover_image, 
    update_image, 
)
from luxury_fashion.apps.products.schemas.produc_image_schema import ImageOut, ImageUpdateIn
from luxury_fashion.apps.products.selectors.product_image_selector import (
    get_image_by_id,
    get_images_by_product,
)
from luxury_fashion.apps.products.selectors.product_selector import get_product_by_id


def _get_image_or_raise(image_id: uuid.UUID):
    image = get_image_by_id(image_id)
    if image is None:
        raise ImageNotFound()
    return image


# ── Leitura ──────────────────────────────────────────────────────────────

def get_image_for_all(image_id: uuid.UUID) -> ImageOut:
    image = _get_image_or_raise(image_id)
    return ImageOut.from_orm(image)


def list_images_for_all(product_id: uuid.UUID) -> list[ImageOut]:
    images = get_images_by_product(product_id)
    return [ImageOut.from_orm(image) for image in images]


# ── Escrita ──────────────────────────────────────────────────────────────

def upload_image_for_admin(
    product_id: uuid.UUID,
    image: UploadedFile,
    is_cover: bool = False,
    display_order: int = 0,
) -> ImageOut:
    product = get_product_by_id(product_id)
    if product is None:
        raise ProductNotFound()

    try:
        validate_image_file(image)
    except DjangoValidationError as exc:
        raise InvalidImageFile(exc.messages[0] if getattr(exc, "messages", None) else str(exc))

    created = create_image(
        product_id=product,
        product_image=image,
        is_cover=is_cover,
        display_order=display_order,
    )
    return ImageOut.from_orm(created)


def update_image_for_admin(image_id: uuid.UUID, data: ImageUpdateIn) -> ImageOut:
    image = _get_image_or_raise(image_id)
    image = update_image(image, **data.dict(exclude_unset=True))
    return ImageOut.from_orm(image)


def delete_image_for_admin(image_id: uuid.UUID) -> None:
    image = _get_image_or_raise(image_id)
    delete_image(image)


def set_cover_image_for_admin(image_id: uuid.UUID) -> ImageOut:
    image = _get_image_or_raise(image_id)
    image = set_cover_image(image)
    return ImageOut.from_orm(image)


def reorder_image_for_admin(image_id: uuid.UUID, display_order: int) -> ImageOut:
    image = _get_image_or_raise(image_id)
    image = reorder_image(image, display_order)
    return ImageOut.from_orm(image)