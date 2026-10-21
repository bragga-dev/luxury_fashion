from django.utils import timezone
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.chat.models.conversation_model import Conversation


def create_conversation(*, client: User, order=None, subject: str = "",) -> Conversation:
    conversation = Conversation(
        client=client,
        order=order,
        subject=subject,
        status=Conversation.Status.OPEN,
    )
    conversation.full_clean()
    conversation.save()
    return conversation


def close_conversation(conversation: Conversation) -> Conversation:
    conversation.close_conversation()
    return conversation


def open_conversation(conversation: Conversation) -> Conversation:
    conversation.open_conversation()
    return conversation


def touch_last_message(conversation: Conversation, when=None) -> None:
    conversation.last_message_at = when or timezone.now()
    conversation.save(update_fields=["last_message_at"])