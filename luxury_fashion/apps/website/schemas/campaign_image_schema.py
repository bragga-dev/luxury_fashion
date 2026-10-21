import uuid
from typing import Literal, Optional

from ninja import Schema

from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage


class CampaignImageUpdateIn(Schema):
    is_cover: Optional[bool] = None
    display_order: Optional[int] = None
    fit: Optional[Literal["cover", "contain"]] = None
    focus_x: Optional[int] = None
    focus_y: Optional[int] = None
    zoom: Optional[float] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None


class CampaignImageOut(Schema):
    campaign_mage_id: uuid.UUID
    campaign_id: uuid.UUID
    image_url: str
    is_cover: bool
    display_order: int
    fit: str = "cover"
    focus_x: int = 50
    focus_y: int = 50
    zoom: float = 1.0
    title: str = ""
    subtitle: str = ""

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
            fit=campaign_image.fit,
            focus_x=campaign_image.focus_x,
            focus_y=campaign_image.focus_y,
            zoom=campaign_image.zoom,
            title=campaign_image.title,
            subtitle=campaign_image.subtitle,

        )