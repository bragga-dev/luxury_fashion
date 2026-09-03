"""
Product Services — orquestra regras de negócio de produtos
(repositories + selectors), devolvendo sempre schemas prontos
para a camada de API.
"""
import uuid
from typing import Optional

from django.db import transaction

from luxury_fashion.apps.core.exceptions.products_exception import (
    CategoryNotFound,
    ProductNameAlreadyExists,
    ProductNotFound,
)
from luxury_fashion.apps.products.repositories.product_repository import (
    activate_product,
    create_product,
    deactivate_product,
    delete_product,
    update_product,
)
from luxury_fashion.apps.products.schemas.product_schema import (
    ProductCreateFullIn,
    ProductCreateIn,
    ProductListOut,
    ProductOut,
    ProductUpdateIn,
)
from luxury_fashion.apps.products.selectors.product_category_selector import get_category_by_id
from luxury_fashion.apps.products.selectors.product_selector import (
    filter_products,
    get_all_products,
    get_product_by_id,
    product_name_exists,
)


def _get_product_or_raise(product_id: uuid.UUID):
    product = get_product_by_id(product_id)
    if product is None:
        raise ProductNotFound()
    return product


# ── Leitura ──────────────────────────────────────────────────────────────

def get_product_for_all(product_id: uuid.UUID) -> ProductOut:
    product = _get_product_or_raise(product_id=product_id)
    return ProductOut.from_orm(product)


def list_products_for_all(active_only: bool = True) -> list[ProductListOut]:
    products = get_all_products(active_only=active_only)
    return [ProductListOut.from_orm(product) for product in products]


def search_products_for_all(
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    in_stock_only: bool = False,
    active_only: bool = True,
) -> list[ProductListOut]:
    """Filtro combinado da vitrine — usado pela busca/listagem pública."""
    products = filter_products(
        search=search,
        product_category_id=product_category_id,
        gender=gender,
        size=size,
        color=color,
        in_stock_only=in_stock_only,
        active_only=active_only,
    )
    return [ProductListOut.from_orm(product) for product in products]


def search_products_queryset(
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    in_stock_only: bool = False,
    active_only: bool = True,
):
    """
    Mesma filtragem de `search_products_for_all`, mas devolve o QuerySet
    bruto (sem serializar) para paginação na camada de router.
    """
    return filter_products(
        search=search,
        product_category_id=product_category_id,
        gender=gender,
        size=size,
        color=color,
        in_stock_only=in_stock_only,
        active_only=active_only,
    )


# ── Escrita ──────────────────────────────────────────────────────────────

def create_product_for_amdin(data: ProductCreateIn) -> ProductOut:
    category = get_category_by_id(product_category_id=data.product_category_id)
    if category is None:
        raise CategoryNotFound()

    if product_name_exists(data.product_name):
        raise ProductNameAlreadyExists()

    product = create_product(product_name=data.product_name, product_category_id=category,)
    return ProductOut.from_orm(product)


def create_product_full_for_admin(
    data: ProductCreateFullIn,
    images: Optional[list] = None,
    cover_index: int = 0,
) -> ProductOut:
   
    from luxury_fashion.apps.products.services.product_image_service import (
        upload_image_for_admin,
    )
    from luxury_fashion.apps.products.services.product_shipping_service import (
        create_shipping_for_admin,
    )
    from luxury_fashion.apps.products.services.product_variant_service import (
        create_variant_for_admin,
    )

    images = images or []

    with transaction.atomic():
        product = create_product_for_amdin(ProductCreateIn(product_name=data.product_name, product_category_id=data.product_category_id,))
        variant = create_variant_for_admin(product_id=product.product_id, data=data.variant)
        create_shipping_for_admin(variant_id=variant.variant_id, data=data.shipping)

        for index, image_file in enumerate(images):
            upload_image_for_admin(
                product.product_id,
                image_file,
                is_cover=(index == cover_index),
                display_order=index,
            )

    return get_product_for_all(product_id=product.product_id)


def update_product_for_admin(product_id: uuid.UUID, data: ProductUpdateIn) -> ProductOut:
    product = _get_product_or_raise(product_id=product_id)

    if data.product_name is not None and product_name_exists(product_name=data.product_name, exclude_id=product_id):
        raise ProductNameAlreadyExists()

    fields = {
        key: value
        for key, value in data.dict(exclude_unset=True).items()
        if value is not None
    }

    if "product_category_id" in fields:
        category = get_category_by_id(fields["product_category_id"])
        if category is None:
            raise CategoryNotFound()
        fields["product_category_id"] = category

    product = update_product(product=product, **fields)
    return ProductOut.from_orm(product)


def delete_product_for_admin(product_id: uuid.UUID) -> None:
    product = _get_product_or_raise(product_id=product_id)
    delete_product(product=product)


def activate_product_for_admin(product_id: uuid.UUID) -> ProductOut:
    product = _get_product_or_raise(product_id=product_id)
    product = activate_product(product=product)
    return ProductOut.from_orm(product)


def deactivate_product_for_admin(product_id: uuid.UUID) -> ProductOut:
    product = _get_product_or_raise(product_id=product_id)
    product = deactivate_product(product=product)
    return ProductOut.from_orm(product)