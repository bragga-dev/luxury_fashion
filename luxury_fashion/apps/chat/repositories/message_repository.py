# luxury_fashion/apps/chat/repositories/message_repository.py
from django.utils import timezone

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.chat.models.conversation_model import Conversation
from luxury_fashion.apps.chat.models.message_attachment_model import MessageAttachment
from luxury_fashion.apps.chat.models.message_model import Message


def create_message(conversation: Conversation, sender: User, content: str = "") -> Message:
    message = Message(conversation=conversation, sender=sender, content=content)
    message.full_clean()
    message.save()
    return message


def add_attachment(
    message: Message,
    *,
    file,
    file_type: str,
    original_filename: str,
    file_size: int,
) -> MessageAttachment:
    attachment = MessageAttachment(
        message=message,
        file=file,
        file_type=file_type,
        original_filename=original_filename,
        file_size=file_size,
    )
    attachment.full_clean()
    attachment.save()
    return attachment


def mark_as_read(message: Message) -> Message:
    message.is_read = True
    message.read_at = timezone.now()
    message.save(update_fields=["is_read", "read_at"])
    return message