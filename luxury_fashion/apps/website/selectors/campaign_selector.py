"""
Campaign Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from luxury_fashion.apps.website.models.campaign_model import Campaign


def get_campaign_by_id(campaign_id: uuid.UUID) -> Optional[Campaign]:
    return Campaign.objects.filter(campaign_id=campaign_id).first()


def campaign_title_exists(title: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    qs = Campaign.objects.filter(title__iexact=title)
    if exclude_id:
        qs = qs.exclude(campaign_id=exclude_id)
    return qs.exists()


def get_all_campaigns(active_only: bool = False) -> QuerySet[Campaign]:
    qs = Campaign.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("-created_at")


def get_running_campaigns() -> QuerySet[Campaign]:
    """Campanhas ativas e dentro da janela de vigência (se definida)."""
    now = timezone.now()
    qs = Campaign.objects.filter(is_active=True)
    qs = qs.exclude(starts_at__gt=now).exclude(ends_at__lt=now)
    return qs.order_by("-created_at")