"""
Product Repository — persistência de Product.
"""
from luxury_fashion.apps.products.models.product_category_model import ProductCategory
from luxury_fashion.apps.products.models.product_model import Product


def create_product(
    product_name: str,
    product_category_id: ProductCategory,
    is_active: bool = True,
) -> Product:
    product = Product(
        product_name=product_name,
        product_category_id=product_category_id,
        is_active=is_active,
    )
    product.full_clean()
    product.save()
    return product


def update_product(product: Product, **fields) -> Product:
    for attr, value in fields.items():
        if value is not None:
            setattr(product, attr, value)
    product.full_clean()
    product.save()
    return product


def delete_product(product: Product) -> None:
    product.delete()


def activate_product(product: Product) -> Product:
    if not product.is_active:
        product.is_active = True
        product.save(update_fields=["is_active"])
    return product


def deactivate_product(product: Product) -> Product:
    if product.is_active:
        product.is_active = False
        product.save(update_fields=["is_active"])
    return product