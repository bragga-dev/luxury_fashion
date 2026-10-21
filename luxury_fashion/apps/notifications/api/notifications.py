"""
Notification endpoints — central de notificações do usuário autenticado
(cliente ou admin). Sempre escopadas ao `request.auth`: ninguém lê, marca
ou apaga notificação de outro usuário.
"""
import uuid

from django_ratelimit.decorators import ratelimit
from ninja import Router, Status

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions.notification_exception import NotificationNotFound
from luxury_fashion.apps.core.permissions.auth_classes import AllRolesAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.notifications.schemas.notification_schema import (
    MarkAllReadOut,
    NotificationOut,
    UnreadCountOut,
)
from luxury_fashion.apps.notifications.services.notification_service import (
    delete_own_notification,
    get_unread_count,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = Router()


@router.get(
    "",
    response={200: PageOut[NotificationOut]},
    auth=AllRolesAuth(),
    summary="Lista as notificações do usuário (mais novas primeiro)",
)
@ratelimit(key="user", rate="120/m", block=True)
def list_notifications_router(request, page: int = 1, page_size: int = 20, unread_only: bool = False):
    user: User = request.auth
    return Status(200, list_notifications(user.user_id, page=page, page_size=page_size, unread_only=unread_only))


@router.get(
    "/unread-count",
    response={200: UnreadCountOut},
    auth=AllRolesAuth(),
    summary="Quantidade de não lidas (badge do sino)",
)
@ratelimit(key="user", rate="120/m", block=True)
def unread_count_router(request):
    user: User = request.auth
    return Status(200, get_unread_count(user.user_id))


@router.post(
    "/read-all",
    response={200: MarkAllReadOut},
    auth=AllRolesAuth(),
    summary="Marca todas as notificações como lidas",
)
@ratelimit(key="user", rate="30/m", block=True)
def read_all_router(request):
    user: User = request.auth
    return Status(200, mark_all_notifications_read(user.user_id))


@router.post(
    "/{notification_id}/read",
    response={200: NotificationOut, 404: MessageOut},
    auth=AllRolesAuth(),
    summary="Marca uma notificação como lida",
)
@ratelimit(key="user", rate="120/m", block=True)
def read_notification_router(request, notification_id: uuid.UUID):
    try:
        user: User = request.auth
        return Status(200, mark_notification_read(user.user_id, notification_id))
    except NotificationNotFound as e:
        return Status(404, {"detail": str(e)})


@router.delete(
    "/{notification_id}",
    response={204: None, 404: MessageOut},
    auth=AllRolesAuth(),
    summary="Exclui uma notificação do próprio usuário",
)
@ratelimit(key="user", rate="60/m", block=True)
def delete_notification_router(request, notification_id: uuid.UUID):
    try:
        user: User = request.auth
        delete_own_notification(user.user_id, notification_id)
        return Status(204, None)
    except NotificationNotFound as e:
        return Status(404, {"detail": str(e)})