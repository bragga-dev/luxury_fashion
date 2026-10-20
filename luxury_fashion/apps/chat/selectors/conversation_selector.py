from typing import Optional
from uuid import UUID

from django.db.models import QuerySet

from luxury_fashion.apps.chat.models.conversation_model import Conversation


def get_conversation_by_id(conversation_id: UUID) -> Optional[Conversation]:
    return Conversation.objects.select_related("client", "assigned_admin", "order").filter(
        conversation_id=conversation_id
    ).first()


def get_conversations_for_client(client_id: UUID) -> QuerySet[Conversation]:
    return Conversation.objects.select_related("order").filter(client_id=client_id)


def get_all_conversations(status: Optional[str] = None) -> QuerySet[Conversation]:
    qs = Conversation.objects.select_related("client", "assigned_admin", "order").all()
    if status:
        qs = qs.filter(status=status)
    return qs


def user_can_access_conversation(conversation: Conversation, user) -> bool:
    from luxury_fashion.apps.core.permissions.roles import is_admin

    return is_admin(user) or conversation.client_id == user.user_id


def get_open_conversation_for_client_and_order(client, order=None):
    return Conversation.objects.filter(
        client=client,
        order=order,
        status=Conversation.Status.OPEN,
    ).first()