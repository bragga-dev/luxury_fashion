import uuid
from datetime import datetime
from typing import List, Optional

from ninja import Schema

from luxury_fashion.apps.chat.models.conversation_model import Conversation
from luxury_fashion.apps.chat.models.message_attachment_model import MessageAttachment
from luxury_fashion.apps.chat.models.message_model import Message


class AttachmentOut(Schema):
    attachment_id: uuid.UUID
    file_type: str
    original_filename: str
    file_size: int
    url: str

    @staticmethod
    def from_orm(obj: MessageAttachment) -> "AttachmentOut":
        return AttachmentOut(
            attachment_id=obj.attachment_id,
            file_type=obj.file_type,
            original_filename=obj.original_filename,
            file_size=obj.file_size,
            url=obj.file.url,
        )


class MessageOut(Schema):
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    content: str
    is_read: bool
    created_at: datetime
    attachments: List[AttachmentOut] = []

    @staticmethod
    def from_orm(obj: Message) -> "MessageOut":
        sender_name = getattr(getattr(obj.sender, "client_profile", None), "first_name", None) or obj.sender.email
        return MessageOut(
            message_id=obj.message_id,
            conversation_id=obj.conversation_id,
            sender_id=obj.sender_id,
            sender_name=sender_name,
            content=obj.content,
            is_read=obj.is_read,
            created_at=obj.created_at,
            attachments=[AttachmentOut.from_orm(a) for a in obj.attachments.all()],
        )


class ConversationOut(Schema):
    conversation_id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    assigned_admin_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    subject: str
    status: str
    last_message_at: Optional[datetime] = None
    created_at: datetime

    @staticmethod
    def from_orm(obj: Conversation) -> "ConversationOut":
        client_name = getattr(getattr(obj.client, "client_profile", None), "first_name", None) or obj.client.email
        return ConversationOut(
            conversation_id=obj.conversation_id,
            client_id=obj.client_id,
            client_name=client_name,
            assigned_admin_id=obj.assigned_admin_id,
            order_id=obj.order_id,
            subject=obj.subject,
            status=obj.status,
            last_message_at=obj.last_message_at,
            created_at=obj.created_at,
        )


class StartConversationIn(Schema):
    order_id: Optional[uuid.UUID] = None


class SendMessageIn(Schema):
    content: str = ""