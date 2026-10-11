"""
Task periódica — cancela pedidos PENDING que passaram do prazo sem pagamento e
devolve o estoque que ficou reservado. Sem isso, um carrinho abandonado no
checkout trava as unidades pra sempre.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from luxury_fashion.apps.core.exceptions import AsaasAPIError
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.services.order_service import expire_pending_order

logger = logging.getLogger(__name__)


@shared_task
def expire_pending_orders() -> int:
    cutoff = timezone.now() - timedelta(hours=settings.ORDER_PENDING_EXPIRATION_HOURS)
    order_ids = list(
        Order.objects.filter(order_status=Order.StatusOrder.PENDING, created_at__lt=cutoff)
        .values_list("order_id", flat=True)
    )

    expired = 0
    for order_id in order_ids:
        try:
            if expire_pending_order(order_id):
                expired += 1
        except AsaasAPIError:
            logger.exception("Não foi possível anular a cobrança do pedido %s; fica pra próxima rodada.", order_id)
        except Exception:
            logger.exception("Erro ao expirar o pedido %s.", order_id)

    logger.info("expire_pending_orders: %s pedido(s) expirado(s) de %s candidato(s).", expired, len(order_ids))
    return expired