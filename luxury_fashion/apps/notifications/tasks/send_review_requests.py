"""
Task periódica — convida o cliente a avaliar a compra N dias após a entrega.
Janela: entregues entre (hoje - REVIEW_REQUEST_WINDOW_DAYS) e (hoje - REVIEW_REQUEST_DELAY_DAYS),
pra não convidar pedidos antigos quando a feature entra no ar nem flood de pedido recém-entregue.
Idempotente: o dedupe_key + o anti-join do selector garantem 1 convite por pedido.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from luxury_fashion.apps.notifications.selectors.notification_selector import get_order_ids_for_review_request
from luxury_fashion.apps.notifications.services.notification_service import notify_review_request

logger = logging.getLogger(__name__)


@shared_task
def send_review_requests() -> int:
    now = timezone.now()
    delay_days = getattr(settings, "REVIEW_REQUEST_DELAY_DAYS", 3)
    window_days = getattr(settings, "REVIEW_REQUEST_WINDOW_DAYS", 30)

    order_ids = get_order_ids_for_review_request(
        delivered_after=now - timedelta(days=window_days),
        delivered_before=now - timedelta(days=delay_days),
    )
    for order_id in order_ids:
        notify_review_request(order_id)

    logger.info("send_review_requests: %s convite(s) de avaliação criado(s).", len(order_ids))
    return len(order_ids)