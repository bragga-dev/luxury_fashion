"""
Product Selectors — queries de leitura. Nenhuma escrita acontece aqui.

Atenção: `gender`, `size` e `color` moram em ProductVariant, não em
Product — filtrar por qualquer um desses três exige atravessar a
relação `variants`.
"""
import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from luxury_fashion.apps.products.models.product_model import Product


def get_product_by_id(product_id: uuid.UUID) -> Optional[Product]:
    return (
        Product.objects
        .select_related("product_category_id")
        .prefetch_related("variants", "images")
        .filter(product_id=product_id)
        .first()
    )


def product_name_exists(product_name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    qs = Product.objects.filter(product_name__iexact=product_name)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def get_all_products(active_only: bool = True) -> QuerySet[Product]:
    qs = Product.objects.select_related("product_category_id")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def filter_products(
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    in_stock_only: bool = False,
    active_only: bool = True,
) -> QuerySet[Product]:
    """
    Filtro combinado da vitrine. `gender`/`size`/`color` filtram por
    variantes existentes do produto (ex.: gender="masculino" só retorna
    produtos que tenham ao menos uma variante masculina).
    """
    qs = Product.objects.select_related("product_category_id")

    if active_only:
        qs = qs.filter(is_active=True)

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(product_name__icontains=search)
            | Q(product_category_id__category_name__icontains=search)
        )

    if product_category_id:
        qs = qs.filter(product_category_id=product_category_id)

    if gender:
        qs = qs.filter(variants__gender=gender, variants__is_active=True)

    if size:
        qs = qs.filter(variants__size=size, variants__is_active=True)

    if color:
        qs = qs.filter(variants__color=color, variants__is_active=True)

    if in_stock_only:
        qs = qs.filter(variants__is_active=True, variants__stock__gt=0)

    return qs.distinct()