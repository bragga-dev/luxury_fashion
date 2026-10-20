"""
Product Selectors — queries de leitura. Nenhuma escrita acontece aqui.

Atenção: `gender` mora em Product; `size` e `color` moram em
ProductVariant — filtrar por eles exige atravessar a relação `variants`.
"""
import uuid
from typing import Optional

from decimal import Decimal

from django.db.models import (
    Avg,
    Count,
    DecimalField,
    Exists,
    F,
    IntegerField,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
)

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


def _with_rating(qs: QuerySet[Product]) -> QuerySet[Product]:
    """
    Anota `avg_rating`/`total_reviews` (só avaliações AUTORIZADAS) via subquery — sem join, então
    não duplica linhas nem conflita com o filtro de variantes.
    """
    from luxury_fashion.apps.reviews.models.reviews_model import Reviews  # import tardio: evita ciclo de apps

    base = (
        Reviews.objects.filter(
            is_authorized=True,
            order_item_id__variant_id__product_id=OuterRef("pk"),
        )
        .order_by()
        .values("order_item_id__variant_id__product_id")
    )
    return qs.annotate(
        avg_rating=Subquery(base.annotate(a=Avg("reviews")).values("a")[:1], output_field=DecimalField()),
        total_reviews=Subquery(base.annotate(c=Count("pk")).values("c")[:1], output_field=IntegerField()),
    )


def get_product_by_id(product_id: uuid.UUID) -> Optional[Product]:
    qs = _with_rating(Product.objects.select_related("product_category_id").prefetch_related("variants", "images"))
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
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
) -> QuerySet[Product]:
    """
    Filtro combinado da vitrine. `gender` filtra direto no produto; `size`/`color`/estoque/preço
    filtram por VARIANTES ativas.

    Os critérios de variante entram TODOS no mesmo `Exists` — ou seja, precisam ser satisfeitos pela
    MESMA variante (size=M & color=black só retorna produto que tenha a variante M-preta, e não
    "uma M qualquer" + "uma preta qualquer", que é o que dois `.filter(variants__...)` separados fariam).

    `sort`: None/"name" mantém a ordenação alfabética de `Product.Meta`; "recent" (mais novos primeiro,
    seção "Novidades"), "price_asc"/"price_desc" (menor preço entre as variantes ativas) e "rating"
    (média das avaliações autorizadas).
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

    variant_conditions = Q(is_active=True)
    has_variant_filter = False
    if size:
        variant_conditions &= Q(size=size)
        has_variant_filter = True
    if color:
        variant_conditions &= Q(color=color)
        has_variant_filter = True
    if in_stock_only:
        variant_conditions &= Q(stock__gt=0)
        has_variant_filter = True
    if min_price is not None:
        variant_conditions &= Q(price__gte=min_price)
        has_variant_filter = True
    if max_price is not None:
        variant_conditions &= Q(price__lte=max_price)
        has_variant_filter = True

    if has_variant_filter:
        qs = qs.filter(
            Exists(ProductVariant.objects.filter(variant_conditions, product_id=OuterRef("pk")))
        )

    if sort == "recent":
        qs = qs.order_by("-created_at")
    elif sort in ("price_asc", "price_desc"):
        cheapest = (
            ProductVariant.objects.filter(product_id=OuterRef("pk"), is_active=True)
            .order_by()
            .values("product_id")
            .annotate(m=Min("price"))
            .values("m")[:1]
        )
        qs = qs.annotate(_min_price=Subquery(cheapest, output_field=DecimalField()))
        qs = qs.order_by(
            F("_min_price").asc(nulls_last=True) if sort == "price_asc" else F("_min_price").desc(nulls_last=True),
            "product_name",
        )
    elif sort == "rating":
        qs = _with_rating(qs).order_by(
            F("avg_rating").desc(nulls_last=True), F("total_reviews").desc(nulls_last=True), "product_name"
        )
        return _with_variants_and_images(qs)

    return _with_variants_and_images(_with_rating(qs))