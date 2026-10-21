"""Selectors de Notification — só leitura."""
from datetime import datetime
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


def get_order_ref(order_id: UUID):
    """
    Pedido "magro" (só id, dono e código) pra montar notificação — sem o
    prefetch de itens/imagens do `get_order_by_id`. Import local evita ciclo
    (payments.services importa notifications.services).
    """
    from luxury_fashion.apps.payments.models.order_model import Order

    return Order.objects.only("order_id", "user_id", "code").filter(order_id=order_id).first()


def get_order_ids_for_review_request(*, delivered_after: datetime, delivered_before: datetime, limit: int = 500) -> list[UUID]:
    """
    Pedidos entregues na janela (delivered_after < entrega <= delivered_before) que ainda têm
    ao menos um item sem avaliação e que AINDA não receberam o convite. O anti-join com as
    notificações evita reprocessar (e bater no unique do dedupe) a cada execução da task.
    """
    from luxury_fashion.apps.payments.models.order_model import Order

    already_invited = Notification.objects.filter(
        type=Notification.NotificationType.REVIEW_REQUEST,
        target_type=Notification.TargetType.ORDER,
        target_id__isnull=False,
    ).values("target_id")

    return list(
        Order.objects.filter(
            order_status=Order.StatusOrder.COMPLETED,
            shipping_status=Order.ShippingStatus.DELIVERED,
            delivered_at__gt=delivered_after,
            delivered_at__lte=delivered_before,
            items__reviews__isnull=True,
        )
        .exclude(order_id__in=already_invited)
        .values_list("order_id", flat=True)
        .distinct()[:limit]
    )


def get_active_admin_ids(*, exclude_id: Optional[UUID] = None) -> list[UUID]:
    """IDs dos admins ativos (destino das notificações administrativas)."""
    qs = User.objects.filter(role=User.UserRole.ADMIN, is_active=True)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return list(qs.values_list("user_id", flat=True))