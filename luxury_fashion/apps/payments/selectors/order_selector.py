"""
Order Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import Prefetch, QuerySet

from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order


def _with_items(qs: QuerySet[Order]) -> QuerySet[Order]:
    items_qs = OrderItem.objects.select_related(
        "variant_id__product_id__product_category_id"
    ).prefetch_related("variant_id__product_id__images")
    return qs.select_related("shipping_address").prefetch_related(Prefetch("items", queryset=items_qs))


def get_order_by_id(order_id: uuid.UUID) -> Optional[Order]:
    return _with_items(Order.objects).filter(order_id=order_id).first()


def get_order_by_id_and_user(order_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Order]:
    return _with_items(Order.objects).filter(order_id=order_id, user_id=user_id).first()


def get_orders_by_user(user_id: uuid.UUID) -> QuerySet[Order]:
    return _with_items(Order.objects).filter(user_id=user_id).order_by("-created_at")