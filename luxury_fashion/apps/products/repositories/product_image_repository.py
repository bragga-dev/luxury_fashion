"""
ProductImage Repository — persistência de ProductImage.
"""
from django.core.files import File
from django.db import transaction

from luxury_fashion.apps.core.tasks.media import delete_old_media_file
from luxury_fashion.apps.products.models.product_image_model import ProductImage
from luxury_fashion.apps.products.models.product_model import Product

@transaction.atomic
def create_image(
    product_id: Product,
    product_image: File,
    is_cover: bool = False,
    display_order: int = 0,
) -> ProductImage:
    image = ProductImage(
        product_id=product_id,
        product_image=product_image,
        is_cover=is_cover,
        display_order=display_order,
    )
    if is_cover:
        ProductImage.objects.filter(product_id=product_id, is_cover=True).update(is_cover=False)
    image.full_clean()
    image.save()
    return image


def update_image(image: ProductImage, **fields) -> ProductImage:
    for attr, value in fields.items():
        if value is not None:
            setattr(image, attr, value)
    image.full_clean()
    image.save()
    return image


def delete_image(image: ProductImage) -> None:
    old_name = image.product_image.name if image.product_image else None
    image.delete()
    if old_name:
        delete_old_media_file.delay(old_name)


@transaction.atomic
def set_cover_image(image: ProductImage) -> ProductImage:
    """
    Promove `image` a capa do produto, removendo a marcação da capa atual (se existir).
    """
    ProductImage.objects.filter(product_id=image.product_id, is_cover=True).exclude(pk=image.pk).update(is_cover=False)
    image.is_cover = True
    image.save(update_fields=["is_cover"])
    return image


def reorder_image(image: ProductImage, display_order: int) -> ProductImage:
    image.display_order = display_order
    image.save(update_fields=["display_order"])
    return image