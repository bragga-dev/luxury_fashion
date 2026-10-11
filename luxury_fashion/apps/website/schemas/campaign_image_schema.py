import uuid
from typing import Optional

from ninja import Schema

from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage


class CampaignImageUpdateIn(Schema):
    is_cover: Optional[bool] = None
    display_order: Optional[int] = None


class CampaignImageOut(Schema):
    campaign_mage_id: uuid.UUID
    campaign_id: uuid.UUID
    image_url: str
    is_cover: bool
    display_order: int

    @classmethod
    def from_orm(cls, campaign_image: CampaignImage) -> "CampaignImageOut":
        try:
            url = campaign_image.image.url
        except Exception:
            url = ""
        return cls(
            campaign_mage_id=campaign_image.campaign_mage_id,
            campaign_id=campaign_image.campaign_id_id,
            image_url=url,
            is_cover=campaign_image.is_cover,
            display_order=campaign_image.display_order,
        )


class CampaignImageListOut(Schema):
    items: list[CampaignImageOut]