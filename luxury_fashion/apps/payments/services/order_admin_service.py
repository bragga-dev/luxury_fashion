"""
Service do painel admin de pedidos — leitura (listagem, detalhe, totais).
A operação de envio fica em order_shipping_service / order_delivery_service.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from luxury_fashion.apps.core.exceptions import OrderNotFound
from luxury_fashion.apps.core.schemas.deafult_schema import PageOut
from luxury_fashion.apps.core.utils.pagination import paginate_queryset
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.schemas.order_admin_schema import (
    OrderAdminListOut,
    OrderAdminOut,
    OrderSummaryOut,
)
from luxury_fashion.apps.payments.selectors.order_selector import (
    get_order_admin_by_id,
    get_orders_summary,
    list_orders_admin,
)


def list_orders_for_admin(
    *,
    page: int = 1,
    page_size: int = 20,
    order_status: Optional[str] = None,
    shipping_status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PageOut[OrderAdminListOut]:
    qs = list_orders_admin(
        order_status=order_status,
        shipping_status=shipping_status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return paginate_queryset(qs, page, page_size, OrderAdminListOut.from_orm)


def get_order_for_admin(order_id: uuid.UUID) -> OrderAdminOut:
    order = get_order_admin_by_id(order_id)
    if order is None:
        raise OrderNotFound()
    return OrderAdminOut.from_orm(order)


def get_orders_summary_for_admin(
    *, date_from: Optional[date] = None, date_to: Optional[date] = None
) -> OrderSummaryOut:
    raw = get_orders_summary(date_from=date_from, date_to=date_to)
    # Preenche com 0 os status sem pedidos: o front não precisa tratar chave ausente.
    by_status = {s: raw["by_status"].get(s, 0) for s in Order.StatusOrder.values}
    by_shipping = {s: raw["by_shipping_status"].get(s, 0) for s in Order.ShippingStatus.values}
    cents = Decimal("0.01")
    return OrderSummaryOut(
        total_orders=raw["total_orders"],
        by_status=by_status,
        by_shipping_status=by_shipping,
        awaiting_shipment=by_shipping[Order.ShippingStatus.PENDING] + by_shipping[Order.ShippingStatus.LABEL_GENERATED],
        revenue=Decimal(raw["revenue"]).quantize(cents),
        average_ticket=Decimal(raw["average_ticket"]).quantize(cents),
    )