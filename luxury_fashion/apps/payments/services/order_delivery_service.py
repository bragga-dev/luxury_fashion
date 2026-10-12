# luxury_fashion/luxury_fashion/apps/payments/services/order_delivery_service.py
"""
Entrega do pedido. Dois caminhos levam a DELIVERED:
  1. webhook da Frenet (frenet_webhook_service), quando FRENET_SHIPMENT_DELIVERED_STATUS está configurado;
  2. ação manual do admin (aqui) — fallback pra webhook perdido ou entrega fora da Frenet.
Ambos usam Order.mark_delivered() e disparam a mesma notificação.
"""
import uuid

from django.db import transaction

from luxury_fashion.apps.core.exceptions import OrderNotFound
from luxury_fashion.apps.core.exceptions.shipping import OrderDeliveryNotAllowed
from luxury_fashion.apps.notifications.services.notification_service import notify_order_delivered
from luxury_fashion.apps.payments.models.order_model import Order


@transaction.atomic
def mark_order_as_delivered(order_id: uuid.UUID) -> Order:
    """
    Idempotente: pedido já entregue é devolvido como está (sem nova notificação).
    Só pedidos pagos que já tiveram etiqueta gerada podem ser marcados.
    """
    order = Order.objects.select_for_update().filter(order_id=order_id).first()
    if order is None:
        raise OrderNotFound()
    if order.order_status != Order.StatusOrder.COMPLETED:
        raise OrderDeliveryNotAllowed("Só pedidos pagos (status Completo) podem ser marcados como entregues.")
    if order.shipping_status == Order.ShippingStatus.DELIVERED:
        return order
    if order.shipping_status == Order.ShippingStatus.PENDING:
        raise OrderDeliveryNotAllowed("O pedido ainda não teve a etiqueta gerada: gere a etiqueta antes de marcar a entrega.")

    order.mark_delivered()
    notify_order_delivered(order.order_id)
    return order