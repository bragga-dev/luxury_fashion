"""
CampaignImage Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage


def get_campaign_image_by_id(campaign_mage_id: uuid.UUID) -> Optional[CampaignImage]:
    return CampaignImage.objects.select_related("campaign_id").filter(campaign_mage_id=campaign_mage_id).first()


def get_images_by_campaign(campaign_id: uuid.UUID) -> QuerySet[CampaignImage]:
    return CampaignImage.objects.filter(campaign_id=campaign_id).order_by("display_order", "created_at")


def get_cover_image(campaign_id: uuid.UUID) -> Optional[CampaignImage]:
    return CampaignImage.objects.filter(campaign_id=campaign_id, is_cover=True).first()