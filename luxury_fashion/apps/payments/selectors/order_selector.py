"""
Order Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Avg, Count, Prefetch, Q, QuerySet, Sum

from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order


def _with_items(qs: QuerySet[Order]) -> QuerySet[Order]:
    items_qs = OrderItem.objects.select_related("variant_id__product_id__product_category_id").prefetch_related("variant_id__product_id__images")
    return qs.select_related("shipping_address").prefetch_related(Prefetch("items", queryset=items_qs))


def get_order_by_id(order_id: uuid.UUID) -> Optional[Order]:
    return _with_items(Order.objects).filter(order_id=order_id).first()


def get_order_by_id_and_user(order_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Order]:
    return _with_items(Order.objects).filter(order_id=order_id, user_id=user_id).first()


def get_orders_by_user(user_id: uuid.UUID) -> QuerySet[Order]:
    return _with_items(Order.objects).filter(user_id=user_id).order_by("-created_at")

def get_order_item_by_variant(product_id: uuid.UUID):
    return OrderItem.objects.filter(variant_id__product_id=product_id).values_list("order_item_id", flat=True)


def get_order_item_by_id(order_item_id: uuid.UUID) -> Optional[OrderItem]:
    return (
        OrderItem.objects.select_related("order_id", "variant_id__product_id")
        .filter(order_item_id=order_item_id)
        .first()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

def get_order_admin_by_id(order_id: uuid.UUID) -> Optional[Order]:
    """Pedido de qualquer cliente, com itens, endereço e dados do cliente."""
    return (
        _with_items(Order.objects)
        .select_related("user_id__client_profile")
        .filter(order_id=order_id)
        .first()
    )


def _filter_by_created_date(qs: QuerySet[Order], date_from: Optional[date], date_to: Optional[date]) -> QuerySet[Order]:
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def list_orders_admin(
    *,
    order_status: Optional[str] = None,
    shipping_status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> QuerySet[Order]:
    """
    Listagem leve do painel: sem prefetch de itens/imagens (só a contagem de itens).
    `search` casa com código do pedido, e-mail, nome ou sobrenome do cliente.
    """
    qs = (
        Order.objects.select_related("user_id__client_profile")
        .annotate(items_count=Count("items"))
        .order_by("-created_at")
    )
    if order_status:
        qs = qs.filter(order_status=order_status)
    if shipping_status:
        qs = qs.filter(shipping_status=shipping_status)
    term = (search or "").strip()[:100]
    if term:
        qs = qs.filter(
            Q(code__icontains=term)
            | Q(user_id__email__icontains=term)
            | Q(user_id__client_profile__first_name__icontains=term)
            | Q(user_id__client_profile__last_name__icontains=term)
        )
    return _filter_by_created_date(qs, date_from, date_to)


def get_orders_summary(*, date_from: Optional[date] = None, date_to: Optional[date] = None) -> dict:
    """
    Totais do dashboard. Receita e ticket médio consideram só pedidos COMPLETED
    (pagos e não reembolsados); `by_shipping_status` também só conta pedidos pagos.
    """
    qs = _filter_by_created_date(Order.objects.all(), date_from, date_to)
    by_status = {r["order_status"]: r["n"] for r in qs.values("order_status").annotate(n=Count("order_id"))}
    paid = qs.filter(order_status=Order.StatusOrder.COMPLETED)
    by_shipping = {r["shipping_status"]: r["n"] for r in paid.values("shipping_status").annotate(n=Count("order_id"))}
    agg = paid.aggregate(revenue=Sum("total_geral"), average=Avg("total_geral"))
    return {
        "total_orders": sum(by_status.values()),
        "by_status": by_status,
        "by_shipping_status": by_shipping,
        "revenue": agg["revenue"] or Decimal("0"),
        "average_ticket": agg["average"] or Decimal("0"),
    }