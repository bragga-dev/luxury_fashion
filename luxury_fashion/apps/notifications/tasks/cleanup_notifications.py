"""
Task periódica — retenção. Sem isso a tabela cresce pra sempre.
Lidas: 90 dias. Qualquer uma (inclusive nunca lida): 365 dias.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from luxury_fashion.apps.notifications.repositories.notification_repository import (
    delete_all_before,
    delete_read_before,
)

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_notifications() -> int:
    now = timezone.now()
    read_days = getattr(settings, "NOTIFICATIONS_READ_RETENTION_DAYS", 90)
    any_days = getattr(settings, "NOTIFICATIONS_MAX_RETENTION_DAYS", 365)

    deleted = delete_read_before(now - timedelta(days=read_days))
    deleted += delete_all_before(now - timedelta(days=any_days))

    logger.info("cleanup_old_notifications: %s notificação(ões) removida(s).", deleted)
    return deleted