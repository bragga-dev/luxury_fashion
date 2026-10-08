"""
Product Selectors — queries de leitura. Nenhuma escrita acontece aqui.

Atenção: `gender` mora em Product; `size` e `color` moram em
ProductVariant — filtrar por eles exige atravessar a relação `variants`.
"""
import uuid
from typing import Optional

from django.db.models import Prefetch, Q, QuerySet

from luxury_fashion.apps.products.models.product_image_model import ProductImage
from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def _with_variants_and_images(qs: QuerySet[Product]) -> QuerySet[Product]:
    """
    Prefetch de `variants` (só ativas) e `images` (capa primeiro, depois
    display_order) — evita N+1 quando a listagem serializa variantes e a
    imagem de capa de cada produto.
    """
    return qs.prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
        Prefetch("images", queryset=ProductImage.objects.order_by("-is_cover", "display_order", "created_at")),
    )


def get_product_by_id(product_id: uuid.UUID) -> Optional[Product]:
    qs = Product.objects.select_related("product_category_id").prefetch_related("variants", "images")
    return qs.filter(product_id=product_id).first()


def product_name_exists(product_name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    qs = Product.objects.filter(product_name__iexact=product_name)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def get_all_products(active_only: bool = True) -> QuerySet[Product]:
    qs = Product.objects.select_related("product_category_id")
    if active_only:
        qs = qs.filter(is_active=True)
    return _with_variants_and_images(qs)


def filter_products(
    search: Optional[str] = None,
    product_category_id: Optional[uuid.UUID] = None,
    gender: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    in_stock_only: bool = False,
    active_only: bool = True,
    sort: Optional[str] = None,
) -> QuerySet[Product]:
    """
    Filtro combinado da vitrine. `gender` filtra direto no produto;
    `size`/`color` filtram por variantes ativas existentes do produto
    (ex.: size="M" só retorna produtos que tenham ao menos uma variante M).

    `sort`: None (default) mantém a ordenação alfabética de `Product.Meta`
    (usada no catálogo/busca). `"recent"` ordena pelos mais recém-criados
    primeiro — usado na seção "Novidades" da home.
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
        qs = qs.filter(gender=gender)

    if size:
        qs = qs.filter(variants__size=size, variants__is_active=True)

    if color:
        qs = qs.filter(variants__color=color, variants__is_active=True)

    if in_stock_only:
        qs = qs.filter(variants__is_active=True, variants__stock__gt=0)

    qs = qs.distinct()
    if sort == "recent":
        qs = qs.order_by("-created_at")

    return _with_variants_and_images(qs)