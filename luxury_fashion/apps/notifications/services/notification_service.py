"""
Service layer de Notifications.

Dois lados:
- PRODUTOR (`notify*`): chamado pelos outros apps quando algo acontece
  (pagamento confirmado, pedido enviado...). Nunca levanta exceção: uma
  notificação que falha não pode derrubar pagamento/pedido.
- CONSUMIDOR (`list_*`, `mark_*`...): usado pelos endpoints /notifications.

Regra de ouro: produtores usam `*_on_commit`. A notificação só nasce depois
que a transação do pedido/pagamento foi confirmada — sem notificação de algo
que sofreu rollback.
"""
import logging
from typing import Optional
from uuid import UUID

from django.db import transaction

from luxury_fashion.apps.core.exceptions.notification_exception import NotificationNotFound
from luxury_fashion.apps.core.schemas.deafult_schema import PageOut
from luxury_fashion.apps.core.utils.pagination import paginate_queryset
from luxury_fashion.apps.notifications.repositories.notification_repository import (
    bulk_create_notifications,
    create_notification,
    delete_notification,
    mark_all_as_read,
    mark_as_read,
)
from luxury_fashion.apps.notifications.schemas.notification_schema import (
    MarkAllReadOut,
    NotificationOut,
    UnreadCountOut,
)
from luxury_fashion.apps.notifications.selectors.notification_selector import (
    count_unread,
    get_active_admin_ids,
    get_notification_for_user,
    get_notifications_for_user,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Produtor
# ═══════════════════════════════════════════════════════════════════════════════

def notify(
    *,
    user_id: UUID,
    notification_type: str,
    title: str,
    body: str = "",
    data: Optional[dict] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    try:
        create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
            dedupe_key=dedupe_key,
        )
    except Exception:
        logger.exception("Falha ao criar notificação (user=%s, type=%s).", user_id, notification_type)


def notify_admins(
    *,
    notification_type: str,
    title: str,
    body: str = "",
    data: Optional[dict] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    try:
        bulk_create_notifications(
            user_ids=get_active_admin_ids(),
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
            dedupe_key=dedupe_key,
        )
    except Exception:
        logger.exception("Falha ao notificar admins (type=%s).", notification_type)


def notify_on_commit(**kwargs) -> None:
    """Agenda `notify` para depois do commit da transação corrente."""
    transaction.on_commit(lambda: notify(**kwargs), robust=True)


def notify_admins_on_commit(**kwargs) -> None:
    transaction.on_commit(lambda: notify_admins(**kwargs), robust=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Consumidor (endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

def list_notifications(
    user_id: UUID, *, page: int = 1, page_size: int = 20, unread_only: bool = False
) -> PageOut[NotificationOut]:
    qs = get_notifications_for_user(user_id, unread_only=unread_only)
    return paginate_queryset(qs, page, page_size, NotificationOut.from_orm)


def get_unread_count(user_id: UUID) -> UnreadCountOut:
    return UnreadCountOut(unread=count_unread(user_id))


def mark_notification_read(user_id: UUID, notification_id: UUID) -> NotificationOut:
    notification = get_notification_for_user(user_id, notification_id)
    if notification is None:
        raise NotificationNotFound()
    if not notification.is_read:
        mark_as_read(user_id=user_id, notification_id=notification_id)
        notification.refresh_from_db(fields=["read_at"])
    return NotificationOut.from_orm(notification)


def mark_all_notifications_read(user_id: UUID) -> MarkAllReadOut:
    return MarkAllReadOut(updated=mark_all_as_read(user_id=user_id))


def delete_own_notification(user_id: UUID, notification_id: UUID) -> None:
    if not delete_notification(user_id=user_id, notification_id=notification_id):
        raise NotificationNotFound()