"""
Campaign Services — orquestra regras de negócio de campanhas
promocionais (repositories + selectors), devolvendo sempre schemas
prontos para a camada de API.
"""
import uuid

from luxury_fashion.apps.core.exceptions.campaign_exception import (
    CampaignNotFound,
    CampaignTitleAlreadyExists,
)
from luxury_fashion.apps.website.repositories.campaign_repository import (
    activate_campaign,
    create_campaign,
    deactivate_campaign,
    delete_campaign,
    update_campaign,
)
from luxury_fashion.apps.website.schemas.campaign_schema import (
    CampaignCreateIn,
    CampaignOut,
    CampaignUpdateIn,
)
from luxury_fashion.apps.website.selectors.campaign_selector import (
    campaign_title_exists,
    get_all_campaigns,
    get_campaign_by_id,
    get_running_campaigns,
)


def _get_campaign_or_raise(campaign_id: uuid.UUID):
    campaign = get_campaign_by_id(campaign_id)
    if campaign is None:
        raise CampaignNotFound()
    return campaign


# ── Leitura ──────────────────────────────────────────────────────────────

def get_campaign_for_all(campaign_id: uuid.UUID) -> CampaignOut:
    campaign = _get_campaign_or_raise(campaign_id)
    return CampaignOut.from_orm(campaign)


def list_campaigns_queryset(active_only: bool = False):
    """QuerySet bruto de campanhas, para paginação na camada de router."""
    return get_all_campaigns(active_only=active_only)


def list_running_campaigns_for_all() -> list[CampaignOut]:
    """Campanhas ativas e dentro da janela de vigência — uso público (home/vitrine)."""
    return [CampaignOut.from_orm(campaign) for campaign in get_running_campaigns()]


# ── Escrita ──────────────────────────────────────────────────────────────

def create_campaign_for_admin(data: CampaignCreateIn) -> CampaignOut:
    if campaign_title_exists(data.title):
        raise CampaignTitleAlreadyExists()

    campaign = create_campaign(**data.dict())
    return CampaignOut.from_orm(campaign)


def update_campaign_for_admin(campaign_id: uuid.UUID, data: CampaignUpdateIn) -> CampaignOut:
    campaign = _get_campaign_or_raise(campaign_id)

    fields = data.dict(exclude_unset=True)
    if "title" in fields and fields["title"] is not None and campaign_title_exists(
        fields["title"], exclude_id=campaign_id
    ):
        raise CampaignTitleAlreadyExists()

    campaign = update_campaign(campaign, **fields)
    return CampaignOut.from_orm(campaign)


def delete_campaign_for_admin(campaign_id: uuid.UUID) -> None:
    campaign = _get_campaign_or_raise(campaign_id)
    delete_campaign(campaign)


def activate_campaign_for_admin(campaign_id: uuid.UUID) -> CampaignOut:
    campaign = _get_campaign_or_raise(campaign_id)
    campaign = activate_campaign(campaign)
    return CampaignOut.from_orm(campaign)


def deactivate_campaign_for_admin(campaign_id: uuid.UUID) -> CampaignOut:
    campaign = _get_campaign_or_raise(campaign_id)
    campaign = deactivate_campaign(campaign)
    return CampaignOut.from_orm(campaign)