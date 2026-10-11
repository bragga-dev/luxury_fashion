from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema

from luxury_fashion.apps.notifications.models.notification_model import Notification


class NotificationOut(Schema):
    notification_id: UUID
    type: str
    title: str
    body: str
    action_url: str
    target_type: str
    target_id: Optional[UUID] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, n: Notification) -> "NotificationOut":
        # `actor` NÃO é exposto: evita vazar o ID de admins pro cliente.
        return cls(
            notification_id=n.notification_id,
            type=n.type,
            title=n.title,
            body=n.body,
            action_url=n.action_url,
            target_type=n.target_type,
            target_id=n.target_id,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at,
        )


class UnreadCountOut(Schema):
    unread: int


class MarkAllReadOut(Schema):
    updated: int