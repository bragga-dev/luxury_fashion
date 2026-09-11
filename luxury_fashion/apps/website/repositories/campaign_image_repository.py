"""
CampaignImage Repository — persistência de CampaignImage.
"""

from django.core.files import File
from django.db import transaction

from luxury_fashion.apps.core.tasks.media import delete_old_media_file
from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage


@transaction.atomic
def create_campaign_image(
    campaign,
    image: File,
    is_cover: bool = False,
    display_order: int = 0,
) -> CampaignImage:
    campaign_image = CampaignImage(
        campaign=campaign,
        image=image,
        is_cover=is_cover,
        display_order=display_order,
    )
    campaign_image.full_clean()
    campaign_image.save()
    return campaign_image


def update_campaign_image(campaign_image: CampaignImage, **fields) -> CampaignImage:
    for attr, value in fields.items():
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
    CampaignImage.objects.filter(
        campaign=campaign_image.campaign,
        is_cover=True,
    ).exclude(
        pk=campaign_image.pk,
    ).update(
        is_cover=False,
    )

    campaign_image.is_cover = True
    campaign_image.save(
        update_fields=["is_cover"],
    )

    return campaign_image


def reorder_campaign_image(
    campaign_image: CampaignImage,
    display_order: int,
) -> CampaignImage:

    campaign_image.display_order = display_order
    campaign_image.save(
        update_fields=["display_order"],
    )

    return campaign_image