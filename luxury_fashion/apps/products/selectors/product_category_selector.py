"""
ProductCategory Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.products.models.product_category_model import ProductCategory


def get_category_by_id(product_category_id: uuid.UUID) -> Optional[ProductCategory]:
    return ProductCategory.objects.filter(product_category_id=product_category_id).first()


def category_name_exists(category_name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    qs = ProductCategory.objects.filter(category_name__iexact=category_name)
    if exclude_id:
        qs = qs.exclude(product_category_id=exclude_id)
    return qs.exists()


def get_all_categories(active_only: bool = True) -> QuerySet[ProductCategory]:
    qs = ProductCategory.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("category_name")


def category_has_products(category: ProductCategory) -> bool:
    return category.product_category.exists()