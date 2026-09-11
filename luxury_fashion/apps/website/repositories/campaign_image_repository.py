"""
CampaignImage Repository — persistência de CampaignImage.
"""
from django.core.files import File
from django.db import transaction

from luxury_fashion.apps.core.tasks.media import delete_old_media_file
from luxury_fashion.apps.website.models.campaign_model import Campaign
from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage


@transaction.atomic
def create_campaign_image(
    campaign_id: Campaign,
    image: File,
    is_cover: bool = False,
    display_order: int = 0,
) -> CampaignImage:
    campaign_image = CampaignImage(
        campaign_id=campaign_id,
        image=image,
        is_cover=is_cover,
        display_order=display_order,
    )
    if is_cover:
        CampaignImage.objects.filter(campaign_id=campaign_id, is_cover=True).update(is_cover=False)
    campaign_image.full_clean()
    campaign_image.save()
    return campaign_image


def update_campaign_image(campaign_image: CampaignImage, **fields) -> CampaignImage:
    for attr, value in fields.items():
        if value is not None:
            setattr(campaign_image, attr, value)
    campaign_image.full_clean()
    campaign_image.save()
    return campaign_image


def delete_campaign_image(campaign_image: CampaignImage) -> None:
    old_name = campaign_image.image.name if campaign_image.image else None
    campaign_image.delete()
    if old_name:
        delete_old_media_file.delay(old_name)


@transaction.atomic
def set_cover_campaign_image(campaign_image: CampaignImage) -> CampaignImage:
    """
    Promove `campaign_image` a capa da campanha, removendo a marcação da
    capa atual (se existir).
    """
    CampaignImage.objects.filter(campaign_id=campaign_image.campaign_id, is_cover=True).exclude(
        pk=campaign_image.pk
    ).update(is_cover=False)
    campaign_image.is_cover = True
    campaign_image.save(update_fields=["is_cover"])
    return campaign_image


def reorder_campaign_image(campaign_image: CampaignImage, display_order: int) -> CampaignImage:
    campaign_image.display_order = display_order
    campaign_image.save(update_fields=["display_order"])
    return campaign_image