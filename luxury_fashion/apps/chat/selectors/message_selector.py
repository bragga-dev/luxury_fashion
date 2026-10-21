from uuid import UUID

from django.db.models import QuerySet

from luxury_fashion.apps.chat.models.message_model import Message


def get_messages_for_conversation(conversation_id: UUID) -> QuerySet[Message]:
    return (
        Message.objects.select_related("sender")
        .prefetch_related("attachments")
        .filter(conversation_id=conversation_id)
        .order_by("created_at")
    )


def get_unread_count_for_user(conversation_id: UUID, user_id: UUID) -> int:
    return (Message.objects.filter(conversation_id=conversation_id, is_read=False).exclude(sender_id=user_id).count())

def get_unread_messages_for_reader(conversation_id: UUID, reader_id: UUID) -> QuerySet[Message]:
    """Mensagens não lidas da conversa, excluindo as enviadas pelo próprio leitor."""
    return Message.objects.filter(conversation_id=conversation_id, is_read=False,).exclude(sender_id=reader_id)