"""Selectors de Notification — só leitura."""
from typing import Optional
from uuid import UUID

from django.db.models import QuerySet

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.notifications.models.notification_model import Notification


def get_notifications_for_user(recipient_id: UUID, *, unread_only: bool = False) -> QuerySet[Notification]:
    qs = Notification.objects.filter(recipient_id=recipient_id)
    if unread_only:
        qs = qs.filter(read_at__isnull=True)
    return qs.order_by("-created_at")


def get_notification_for_user(recipient_id: UUID, notification_id: UUID) -> Optional[Notification]:
    return Notification.objects.filter(recipient_id=recipient_id, notification_id=notification_id).first()


def count_unread(recipient_id: UUID) -> int:
    return Notification.objects.filter(recipient_id=recipient_id, read_at__isnull=True).count()


def get_active_admin_ids(*, exclude_id: Optional[UUID] = None) -> list[UUID]:
    """IDs dos admins ativos (destino das notificações administrativas)."""
    qs = User.objects.filter(role=User.UserRole.ADMIN, is_active=True)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return list(qs.values_list("user_id", flat=True))