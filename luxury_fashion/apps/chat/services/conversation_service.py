"""
Conversation Service — abrir/listar conversas.
"""
from typing import Optional
from uuid import UUID

from luxury_fashion.apps.accounts.selectors.user_selector import get_user_by_id
from luxury_fashion.apps.chat.schemas.chat_schema import ConversationOut
from luxury_fashion.apps.chat.selectors.conversation_selector import (
    get_all_conversations,
    get_conversation_by_id,
    get_conversations_for_client,
)
from luxury_fashion.apps.core.exceptions import ConversationNotFound, PermissionDenied, UserNotFound
from luxury_fashion.apps.core.permissions.roles import is_admin
from luxury_fashion.apps.payments.selectors.order_selector import get_order_by_id

from luxury_fashion.apps.chat.repositories.conversation_repository import create_conversation
from luxury_fashion.apps.chat.selectors.conversation_selector import (
    get_open_conversation_for_client_and_order,
)


def start_or_resume_conversation(client_user_id: UUID, order_id: Optional[UUID] = None) -> ConversationOut:
    client = get_user_by_id(user_id=client_user_id)
    if client is None:
        raise UserNotFound()

    order = get_order_by_id(order_id=order_id) if order_id else None

    conversation = get_open_conversation_for_client_and_order(client=client, order=order)
    if conversation is None:
        subject = f"Pedido {order.code}" if order else ""
        conversation = create_conversation(client=client, order=order, subject=subject)

    return ConversationOut.from_orm(conversation)



def get_conversation_for_user(user_id: UUID, conversation_id: UUID) -> ConversationOut:
    conversation = get_conversation_by_id(conversation_id)
    if conversation is None:
        raise ConversationNotFound()

    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    if not is_admin(user) and conversation.client_id != user.user_id:
        raise PermissionDenied("Você não tem acesso a esta conversa.")

    return ConversationOut.from_orm(conversation)


def list_conversations_for_client(client_user_id: UUID) -> list[ConversationOut]:
    conversations = get_conversations_for_client(client_id=client_user_id)
    return [ConversationOut.from_orm(c) for c in conversations]


def list_conversations_for_admin(status: Optional[str] = None) -> list[ConversationOut]:
    conversations = get_all_conversations(status=status)
    return [ConversationOut.from_orm(c) for c in conversations]