"""
ProductCategory Services — orquestra regras de negócio de categorias
de produto (repositories + selectors), devolvendo sempre schemas prontos
para a camada de API.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import UploadedFile

from luxury_fashion.apps.core.exceptions.media import InvalidImageFile
from luxury_fashion.apps.core.exceptions.products_exception import (
    CategoryHasProducts,
    CategoryNameAlreadyExists,
    CategoryNotFound,
)
from luxury_fashion.apps.core.validators.image_validator import validate_image_file
from luxury_fashion.apps.products.repositories.product_category_repository import (
    activate_category, 
    create_category, 
    deactivate_category, 
    delete_category, 
    remove_category_image, 
    set_category_image,
    update_category, 
)
from luxury_fashion.apps.products.schemas.product_category_schema import (
    ProductCategoryCreateIn,
    ProductCategoryOut,
    ProductCategoryUpdateIn,
)
from luxury_fashion.apps.products.selectors.product_category_selector import (
    category_has_products,
    category_name_exists,
    get_all_categories,
    get_category_by_id,
)


def _get_category_or_raise(product_category_id: uuid.UUID):
    category = get_category_by_id(product_category_id)
    if category is None:
        raise CategoryNotFound()
    return category


# ── Leitura ──────────────────────────────────────────────────────────────

def get_category_for_all(product_category_id: uuid.UUID) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)
    return ProductCategoryOut.from_orm(category)


def list_categories_for_all(active_only: bool = True) -> list[ProductCategoryOut]:
    categories = get_all_categories(active_only=active_only)
    return [ProductCategoryOut.from_orm(category) for category in categories]


def list_categories_queryset(active_only: bool = True):
    """QuerySet bruto de categorias, para paginação na camada de router."""
    return get_all_categories(active_only=active_only)


# ── Escrita ──────────────────────────────────────────────────────────────

def create_category_for_admin(data: ProductCategoryCreateIn) -> ProductCategoryOut:
    if category_name_exists(data.category_name):
        raise CategoryNameAlreadyExists()

    category = create_category(category_name=data.category_name)
    return ProductCategoryOut.from_orm(category)


def update_category_for_admin(product_category_id: uuid.UUID, data: ProductCategoryUpdateIn) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)

    if data.category_name is not None and category_name_exists(data.category_name, exclude_id=product_category_id):
        raise CategoryNameAlreadyExists()

    category = update_category(category, **data.dict(exclude_unset=True))
    return ProductCategoryOut.from_orm(category)


def delete_category_for_admin(product_category_id: uuid.UUID) -> None:
    category = _get_category_or_raise(product_category_id)
    if category_has_products(category):
        raise CategoryHasProducts()
    delete_category(category)


def activate_category_for_admin(product_category_id: uuid.UUID) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)
    category = activate_category(category)
    return ProductCategoryOut.from_orm(category)


def deactivate_category_for_admin(product_category_id: uuid.UUID) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)
    category = deactivate_category(category)
    return ProductCategoryOut.from_orm(category)


def upload_category_image_for_admin(product_category_id: uuid.UUID, image: UploadedFile) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)

    try:
        validate_image_file(image)
    except DjangoValidationError as exc:
        raise InvalidImageFile(exc.messages[0] if getattr(exc, "messages", None) else str(exc))

    category = set_category_image(category, image)
    return ProductCategoryOut.from_orm(category)


def remove_category_image_for_admin(product_category_id: uuid.UUID) -> ProductCategoryOut:
    category = _get_category_or_raise(product_category_id)
    category = remove_category_image(category)
    return ProductCategoryOut.from_orm(category)