import uuid
from typing import Optional

from ninja import Schema, Field

from luxury_fashion.apps.accounts.models.admin_model import AdminProfile


class AdminProfileOut(Schema):
    admin_id: uuid.UUID
    full_name: str
    photo_url: Optional[str] = None

    @classmethod
    def from_orm(cls, admin_profile: AdminProfile) -> "AdminProfileOut":
        return cls(
            admin_id=admin_profile.admin_id,
            full_name=admin_profile.full_name,
            photo_url=admin_profile.photo_url,
        )


class AdminProfileUpdateIn(Schema):
    full_name: str = Field(..., min_length=2, max_length=255)