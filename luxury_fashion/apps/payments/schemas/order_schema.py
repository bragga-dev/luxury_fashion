import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from ninja import Schema, Field

from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.schemas.order_item_schema import OrderItemOut


class StatusOrderEnum(str, Enum):
    """Espelha Order.StatusOrder."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class OrderCreateIn(Schema):
    """
    Checkout do carrinho do cliente autenticado. `user_id` e `cart_id`
    NUNCA vêm do payload — são resolvidos a partir de `request.auth` no
    service, senão qualquer cliente autenticado poderia criar pedido em
    nome de outro usuário.
    """
    shipping_address_id: uuid.UUID


class OrderOut(Schema):
    order_id: uuid.UUID
    code: str
    order_status: StatusOrderEnum
    items: List[OrderItemOut] = Field(default_factory=list)
    subtotal: Decimal
    order_shipping_total: Decimal
    total_geral: Decimal
    shipping_address_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, order: Order) -> "OrderOut":
        items = [OrderItemOut.from_orm(item) for item in order.items.all()]
        return cls(
            order_id=order.order_id,
            code=order.code,
            order_status=order.order_status,
            items=items,
            subtotal=order.subtotal,
            order_shipping_total=order.order_shipping_total,
            total_geral=order.total_geral,
            shipping_address_id=order.shipping_address_id,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )