"""
Schemas de saída do painel admin de pedidos. Só leitura: o admin não cria nem
edita pedido/itens aqui (snapshot fiscal imutável) — só consulta e opera o envio.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.schemas.order_schema import OrderOut, ShippingStatusEnum, StatusOrderEnum


def _client_name(user) -> Optional[str]:
    # `client_profile` é reverse OneToOne: sem perfil, o getattr com default devolve None.
    profile = getattr(user, "client_profile", None)
    if profile is None:
        return None
    name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
    return name or None


class OrderAdminListOut(Schema):
    order_id: uuid.UUID
    code: str
    client_name: Optional[str] = None
    client_email: str
    order_status: StatusOrderEnum
    order_status_label: str
    shipping_status: ShippingStatusEnum
    shipping_status_label: str
    items_count: int
    total_geral: Decimal
    shipping_tracking_code: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, order: Order) -> "OrderAdminListOut":
        return cls(
            order_id=order.order_id,
            code=order.code,
            client_name=_client_name(order.user_id),
            client_email=order.user_id.email,
            order_status=order.order_status,
            order_status_label=order.get_order_status_display(),
            shipping_status=order.shipping_status,
            shipping_status_label=order.get_shipping_status_display(),
            items_count=getattr(order, "items_count", 0),
            total_geral=order.total_geral,
            shipping_tracking_code=order.shipping_tracking_code,
            created_at=order.created_at,
        )


class OrderAdminAddressOut(Schema):
    cep: str
    street: str
    number: str
    complement: str = ""
    neighborhood: str
    city: str
    state: str
    country: str


class OrderAdminOut(OrderOut):
    """Detalhe completo do pedido para o admin (inclui cliente, endereço e dados do envio)."""
    client_user_id: uuid.UUID
    client_name: Optional[str] = None
    client_email: str
    shipping_address: Optional[OrderAdminAddressOut] = None
    frenet_order_id: Optional[str] = None
    shipping_label_url: Optional[str] = None
    canceled_at: Optional[datetime] = None
    canceled_reason: Optional[str] = None

    @classmethod
    def from_orm(cls, order: Order) -> "OrderAdminOut":
        base = OrderOut.from_orm(order)
        address = order.shipping_address
        return cls(
            **{name: getattr(base, name) for name in OrderOut.model_fields},
            client_user_id=order.user_id_id,
            client_name=_client_name(order.user_id),
            client_email=order.user_id.email,
            shipping_address=(
                OrderAdminAddressOut(
                    cep=address.cep,
                    street=address.street,
                    number=address.number,
                    complement=address.complement or "",
                    neighborhood=address.neighborhood,
                    city=address.city,
                    state=address.state,
                    country=address.country,
                )
                if address
                else None
            ),
            frenet_order_id=order.frenet_order_id,
            shipping_label_url=order.shipping_label_url,
            canceled_at=order.canceled_at,
            canceled_reason=order.canceled_reason,
        )


class OrderSummaryOut(Schema):
    total_orders: int
    by_status: dict[str, int]
    # Só pedidos pagos (COMPLETED)
    by_shipping_status: dict[str, int]
    awaiting_shipment: int
    revenue: Decimal
    average_ticket: Decimal