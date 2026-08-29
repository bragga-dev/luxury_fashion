"""
ProductVariant Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def get_variant_by_id(variant_id: uuid.UUID) -> Optional[ProductVariant]:
    return ProductVariant.objects.select_related("product_id").filter(variant_id=variant_id).first()


def variant_exists_for_product_size_color_gender(
    product_id: uuid.UUID,
    size: Optional[str],
    color: Optional[str],
    gender: Optional[str],
    exclude_id: Optional[uuid.UUID] = None,
) -> bool:
    qs = ProductVariant.objects.filter(
        product_id=product_id, size=size, color=color, gender=gender,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def get_variants_by_product(product_id: uuid.UUID, active_only: bool = True) -> QuerySet[ProductVariant]:
    qs = ProductVariant.objects.filter(product_id=product_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("size", "color", "gender")


def get_in_stock_variants_by_product(product_id: uuid.UUID) -> QuerySet[ProductVariant]:
    return ProductVariant.objects.filter(product_id=product_id, is_active=True, stock__gt=0)