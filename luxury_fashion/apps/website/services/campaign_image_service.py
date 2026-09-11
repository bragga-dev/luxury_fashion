"""
CampaignImage Services — orquestra regras de negócio de imagens/banners
de campanha (repositories + selectors), devolvendo sempre schemas
prontos para a camada de API.
"""

import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import UploadedFile

from luxury_fashion.apps.core.exceptions.campaign_exception import (
    CampaignImageNotFound,
    CampaignNotFound,
)
from luxury_fashion.apps.core.exceptions.media import InvalidImageFile
from luxury_fashion.apps.core.validators.image_validator import validate_image_file

from luxury_fashion.apps.website.models.campaignImage_model import CampaignImage

from luxury_fashion.apps.website.repositories.campaign_image_repository import (
    create_campaign_image,
    delete_campaign_image,
    reorder_campaign_image,
    set_cover_campaign_image,
    update_campaign_image,
)

from luxury_fashion.apps.website.schemas.campaign_image_schema import (
    CampaignImageOut,
    CampaignImageUpdateIn,
)

from luxury_fashion.apps.website.selectors.campaign_image_selector import (
    get_campaign_image_by_id,
    get_images_by_campaign,
)

from luxury_fashion.apps.website.selectors.campaign_selector import (
    get_campaign_by_id,
)


def _get_campaign_image_or_raise(
    campaign_image_id: uuid.UUID,
) -> CampaignImage:

    campaign_image = get_campaign_image_by_id(campaign_image_id)

    if campaign_image is None:
        raise CampaignImageNotFound()

    return campaign_image


# ── Leitura ──────────────────────────────────────────────────────────────

def get_campaign_image_for_all(
    campaign_image_id: uuid.UUID,
) -> CampaignImageOut:

    campaign_image = _get_campaign_image_or_raise(campaign_image_id)

    return CampaignImageOut.from_orm(campaign_image)


def list_campaign_images_for_all(
    campaign_id: uuid.UUID,
) -> list[CampaignImageOut]:

    images = get_images_by_campaign(campaign_id)

    return [
        CampaignImageOut.from_orm(image)
        for image in images
    ]


# ── Escrita ──────────────────────────────────────────────────────────────

def upload_campaign_image_for_admin(
    campaign_id: uuid.UUID,
    image: UploadedFile,
    is_cover: bool = False,
    display_order: int = 0,
) -> CampaignImageOut:

    campaign = get_campaign_by_id(campaign_id)

    if campaign is None:
        raise CampaignNotFound()

    try:
        validate_image_file(image)
    except DjangoValidationError as exc:
        raise InvalidImageFile(
            exc.messages[0]
            if getattr(exc, "messages", None)
            else str(exc)
        )

    # Regra de negócio:
    # uma nova imagem marcada como capa deve remover
    # a capa atualmente existente.
    if is_cover:
        set_cover = True
    else:
        set_cover = False

    created = create_campaign_image(
        campaign=campaign,
        image=image,
        is_cover=False,
        display_order=display_order,
    )

    if set_cover:
        created = set_cover_campaign_image(created)

    return CampaignImageOut.from_orm(created)


def update_campaign_image_for_admin(
    campaign_image_id: uuid.UUID,
    data: CampaignImageUpdateIn,
) -> CampaignImageOut:

    campaign_image = _get_campaign_image_or_raise(campaign_image_id)

    fields = data.dict(exclude_unset=True)

    campaign_image = update_campaign_image(
        campaign_image,
        **fields,
    )

    return CampaignImageOut.from_orm(campaign_image)


def delete_campaign_image_for_admin(
    campaign_image_id: uuid.UUID,
) -> None:

    campaign_image = _get_campaign_image_or_raise(
        campaign_image_id,
    )

    delete_campaign_image(campaign_image)


def set_cover_campaign_image_for_admin(
    campaign_image_id: uuid.UUID,
) -> CampaignImageOut:

    campaign_image = _get_campaign_image_or_raise(
        campaign_image_id,
    )

    # Regra de negócio:
    # se já é a capa, não há nada a fazer.
    if not campaign_image.is_cover:
        campaign_image = set_cover_campaign_image(
            campaign_image,
        )

    return CampaignImageOut.from_orm(campaign_image)


def reorder_campaign_image_for_admin(
    campaign_image_id: uuid.UUID,
    display_order: int,
) -> CampaignImageOut:

    campaign_image = _get_campaign_image_or_raise(
        campaign_image_id,
    )

    campaign_image = reorder_campaign_image(
        campaign_image,
        display_order,
    )

    return CampaignImageOut.from_orm(campaign_image)