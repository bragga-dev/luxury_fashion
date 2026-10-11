import uuid
from datetime import datetime
from typing import Optional

from ninja import Schema
from pydantic import field_validator, model_validator

from luxury_fashion.apps.website.models.campaign_model import Campaign


class CampaignCreateIn(Schema):
    title: str
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Título não pode ser vazio.")
        return v

    @model_validator(mode="after")
    def validate_period(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("A data de término deve ser posterior à data de início.")
        return self


class CampaignUpdateIn(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Título não pode ser vazio.")
        return v


class CampaignOut(Schema):
    campaign_id: uuid.UUID
    title: str
    description: Optional[str] = None
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, campaign: Campaign) -> "CampaignOut":
        return cls(
            campaign_id=campaign.campaign_id,
            title=campaign.title,
            description=campaign.description,
            is_active=campaign.is_active,
            starts_at=campaign.starts_at,
            ends_at=campaign.ends_at,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )


class CampaignListOut(Schema):
    items: list[CampaignOut]