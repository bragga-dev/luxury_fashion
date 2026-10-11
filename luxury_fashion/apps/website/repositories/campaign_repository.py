"""
Campaign Repository — persistência de Campaign.
"""

from luxury_fashion.apps.website.models.campaign_model import Campaign


def create_campaign(**fields) -> Campaign:
    campaign = Campaign(**fields)
    campaign.full_clean()
    campaign.save()
    return campaign


def update_campaign(campaign: Campaign, **fields) -> Campaign:
    for attr, value in fields.items():
        setattr(campaign, attr, value)
    campaign.full_clean()
    campaign.save()
    return campaign


def delete_campaign(campaign: Campaign) -> None:
    campaign.delete()


def activate_campaign(campaign: Campaign) -> Campaign:
    campaign.is_active = True
    campaign.save(update_fields=["is_active", "updated_at"])
    return campaign


def deactivate_campaign(campaign: Campaign) -> Campaign:
    campaign.is_active = False
    campaign.save(update_fields=["is_active", "updated_at"])
    return campaign