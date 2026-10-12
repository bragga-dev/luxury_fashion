"""
Processamento dos webhooks da Frenet (status do envio e tracking).

Os webhooks só chegam para pedidos criados via API (a URL vai no payload do
OneClick). Casamos o evento com o Order por `code` (Order.Id enviado) e, por
segurança, conferimos o ShipmentId gravado.
"""
import hmac
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from luxury_fashion.apps.notifications.services.notification_service import (
    notify_order_delivered,
    notify_order_in_transit,
    notify_order_shipped,
)
from luxury_fashion.apps.payments.models.order_model import Order

logger = logging.getLogger(__name__)

SHIPMENT_POSTED = 5
SHIPMENT_CANCELLED = 7


def is_valid_webhook_token(headers) -> bool:
    """
    Os webhooks mexem no status de envio dos pedidos, então NÃO ficam abertos: sem
    FRENET_WEBHOOK_TOKEN_VALUE configurado só aceitamos em DEBUG (dev). Em produção, o
    header FRENET_WEBHOOK_TOKEN_NAME com esse valor é obrigatório (avisar a Frenet do par).
    """
    expected = getattr(settings, "FRENET_WEBHOOK_TOKEN_VALUE", "")
    if not expected:
        if not settings.DEBUG:
            logger.error("FRENET_WEBHOOK_TOKEN_VALUE não configurado: webhook Frenet recusado.")
        return bool(settings.DEBUG)
    name = getattr(settings, "FRENET_WEBHOOK_TOKEN_NAME", "FRENET_INTEGRATION")
    # Django expõe o header com hífen ("Frenet-Integration") mesmo que o nome
    # configurado use underscore; sem normalizar, o header nunca casava.
    return hmac.compare_digest(headers.get(name.replace("_", "-"), ""), expected)


def _find_order(order_code: str, shipment_id) -> Order | None:
    order = Order.objects.select_for_update().filter(code=order_code).first()
    if order is None:
        logger.warning("Webhook Frenet: pedido %s não encontrado.", order_code)
        return None
    if order.frenet_order_id and str(order.frenet_order_id) != str(shipment_id):
        logger.warning(
            "Webhook Frenet: ShipmentId divergente (order=%s esperado=%s recebido=%s).",
            order_code, order.frenet_order_id, shipment_id,
        )
        return None
    return order


@transaction.atomic
def handle_status_update(order_code: str, shipment_id: int, shipment_status: int) -> None:
    order = _find_order(order_code, shipment_id)
    if order is None:
        return

    # Código de "entregue" da Frenet: configurável (FRENET_SHIPMENT_DELIVERED_STATUS) porque o
    # valor deve ser confirmado na doc/painel da Frenet. Sem ele, a entrega é marcada pelo admin.
    delivered_code = getattr(settings, "FRENET_SHIPMENT_DELIVERED_STATUS", None)

    if shipment_status == SHIPMENT_POSTED:
        if order.shipping_status in (Order.ShippingStatus.IN_TRANSIT, Order.ShippingStatus.DELIVERED):
            # Evento atrasado/duplicado: não regride um pedido que já avançou.
            logger.info("Webhook Frenet: POSTED ignorado, pedido %s já está %s.", order_code, order.shipping_status)
            return
        was_shipped = order.shipping_status == Order.ShippingStatus.SHIPPED
        order.shipping_status = Order.ShippingStatus.SHIPPED
        order.shipped_at = order.shipped_at or timezone.now()
        order.save(update_fields=["shipping_status", "shipped_at", "updated_at"])
        if not was_shipped:
            notify_order_shipped(order.order_id)
    elif delivered_code is not None and shipment_status == int(delivered_code):
        if (
            order.order_status == Order.StatusOrder.COMPLETED
            and order.shipping_status != Order.ShippingStatus.DELIVERED
        ):
            order.mark_delivered()
            notify_order_delivered(order.order_id)
    elif shipment_status == SHIPMENT_CANCELLED:
        # Etiqueta cancelada na Frenet (reembolso é lá): libera o pedido para nova geração.
        order.shipping_status = Order.ShippingStatus.PENDING
        order.frenet_order_id = None
        order.shipping_label_url = None
        order.shipping_tracking_code = None
        order.shipped_at = None
        order.save(update_fields=[
            "shipping_status", "frenet_order_id", "shipping_label_url",
            "shipping_tracking_code", "shipped_at", "updated_at",
        ])
    else:
        logger.info("Webhook Frenet: status %s ignorado (order=%s).", shipment_status, order_code)


@transaction.atomic
def handle_tracking_update(order_code: str, shipment_id: int, tracking_number: str | None) -> None:
    order = _find_order(order_code, shipment_id)
    if order is None or not tracking_number:
        return
    order.shipping_tracking_code = tracking_number
    # Qualquer evento de tracking após a postagem indica que está a caminho.
    moved_to_transit = order.shipping_status == Order.ShippingStatus.SHIPPED
    if moved_to_transit:
        order.shipping_status = Order.ShippingStatus.IN_TRANSIT
    order.save(update_fields=["shipping_tracking_code", "shipping_status", "updated_at"])
    if moved_to_transit:
        notify_order_in_transit(order.order_id)