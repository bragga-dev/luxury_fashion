"""
ProductImage Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.products.models.product_image_model import ProductImage


def get_image_by_id(image_id: uuid.UUID) -> Optional[ProductImage]:
    return ProductImage.objects.select_related("product_id").filter(image_id=image_id).first()


def get_images_by_product(product_id: uuid.UUID) -> QuerySet[ProductImage]:
    return ProductImage.objects.filter(product_id=product_id).order_by("display_order", "created_at")


def get_cover_image(product_id: uuid.UUID) -> Optional[ProductImage]:
    return ProductImage.objects.filter(product_id=product_id, is_cover=True).first()