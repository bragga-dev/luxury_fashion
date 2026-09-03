"""
ProductCategory Repository — persistência de ProductCategory.
"""
from typing import Optional

from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from luxury_fashion.apps.products.models.product_category_model import ProductCategory
from luxury_fashion.apps.core.tasks.media import delete_old_media_file


def create_category(
    category_name: str,
    category_image: Optional[File] = None,
    is_active: Optional[bool] = None,
) -> ProductCategory:
    fields = {
        "category_name": category_name,
        "category_image": category_image,
        "is_active": is_active,
    }
    fields = {k: v for k, v in fields.items() if v is not None}

    category = ProductCategory(**fields)
    category.full_clean()
    category.save()
    return category


def update_category(category: ProductCategory, **fields) -> ProductCategory:
    for attr, value in fields.items():
        if value is not None:
            setattr(category, attr, value)
    category.full_clean()
    category.save()
    return category


def delete_category(category: ProductCategory) -> None:
    category.delete()


def activate_category(category: ProductCategory) -> ProductCategory:
    if not category.is_active:
        category.is_active = True
        category.save(update_fields=["is_active"])
    return category


def deactivate_category(category: ProductCategory) -> ProductCategory:
    if category.is_active:
        category.is_active = False
        category.save(update_fields=["is_active"])
    return category


def set_category_image(category: ProductCategory, image: File) -> ProductCategory:
    old_name = (
        category.category_image.name
        if category.category_image and category.category_image.name != "default/category_img.jpg"
        else None
    )
    category.category_image = image
    category.full_clean()
    category.save(update_fields=["category_image"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return category


def remove_category_image(category: ProductCategory) -> ProductCategory:
    old_name = (
        category.category_image.name
        if category.category_image and category.category_image.name != "default/category_img.jpg"
        else None
    )
    category.category_image = "default/category_img.jpg"
    category.save(update_fields=["category_image"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return category