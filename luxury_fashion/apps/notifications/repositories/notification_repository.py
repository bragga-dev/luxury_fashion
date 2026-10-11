"""
Repository de Notification — só persistência. Recebe valores já resolvidos
(IDs/strings), sem regra de negócio.
"""
import logging
from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from luxury_fashion.apps.notifications.models.notification_model import Notification

logger = logging.getLogger(__name__)


def create_notification(
    *,
    recipient_id: UUID,
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor_id: Optional[UUID] = None,
    target_type: str = "",
    target_id: Optional[UUID] = None,
    dedupe_key: Optional[str] = None,
) -> Optional[Notification]:
    """
    Cria a notificação. Devolve None se `dedupe_key` já existir pro destinatário
    (evento duplicado). O `atomic` interno é um savepoint: o IntegrityError
    não contamina a transação do caller.
    """
    try:
        with transaction.atomic():
            return Notification.objects.create(
                recipient_id=recipient_id,
                actor_id=actor_id,
                type=notification_type,
                title=title,
                body=body,
                action_url=action_url,
                target_type=target_type,
                target_id=target_id,
                dedupe_key=dedupe_key,
            )
    except IntegrityError:
        logger.info(
            "Notificação ignorada (duplicada ou usuário inexistente): recipient=%s key=%s",
            recipient_id,
            dedupe_key,
        )
        return None


def bulk_create_notifications(
    *,
    recipient_ids: Iterable[UUID],
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor_id: Optional[UUID] = None,
    target_type: str = "",
    target_id: Optional[UUID] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    """Fan-out (admins, campanhas). `ignore_conflicts` respeita o dedupe por destinatário."""
    objs = [
        Notification(
            recipient_id=rid,
            actor_id=actor_id,
            type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            target_type=target_type,
            target_id=target_id,
            dedupe_key=dedupe_key,
        )
        for rid in recipient_ids
    ]
    if objs:
        Notification.objects.bulk_create(objs, batch_size=1000, ignore_conflicts=True)


def mark_as_read(*, recipient_id: UUID, notification_id: UUID) -> int:
    return Notification.objects.filter(
        recipient_id=recipient_id, notification_id=notification_id, read_at__isnull=True
    ).update(read_at=timezone.now())


def mark_all_as_read(*, recipient_id: UUID) -> int:
    return Notification.objects.filter(recipient_id=recipient_id, read_at__isnull=True).update(
        read_at=timezone.now()
    )


def delete_notification(*, recipient_id: UUID, notification_id: UUID) -> bool:
    deleted, _ = Notification.objects.filter(recipient_id=recipient_id, notification_id=notification_id).delete()
    return deleted > 0


def delete_by_target(*, target_type: str, target_id: UUID, notification_type: Optional[str] = None) -> int:
    """Remove notificações ligadas a um objeto (ex.: REVIEW_PENDING de uma avaliação já moderada)."""
    qs = Notification.objects.filter(target_type=target_type, target_id=target_id)
    if notification_type:
        qs = qs.filter(type=notification_type)
    deleted, _ = qs.delete()
    return deleted


def delete_read_before(cutoff: datetime) -> int:
    deleted, _ = Notification.objects.filter(read_at__isnull=False, created_at__lt=cutoff).delete()
    return deleted


def delete_all_before(cutoff: datetime) -> int:
    deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    return deleted