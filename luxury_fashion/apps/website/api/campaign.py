"""
Campaign endpoints — CRUD de campanhas promocionais e de suas
imagens/banners.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile

from luxury_fashion.apps.core.exceptions import (
    CampaignImageNotFound,
    CampaignNotFound,
    CampaignTitleAlreadyExists,
    InvalidImageFile,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.website.schemas.campaign_image_schema import (
    CampaignImageOut,
    CampaignImageUpdateIn,
)
from luxury_fashion.apps.website.schemas.campaign_schema import (
    CampaignCreateIn,
    CampaignOut,
    CampaignUpdateIn,
)
from luxury_fashion.apps.website.services.campaign_image_service import (
    delete_campaign_image_for_admin,
    list_campaign_images_for_all,
    reorder_campaign_image_for_admin,
    set_cover_campaign_image_for_admin,
    update_campaign_image_for_admin,
    upload_campaign_image_for_admin,
)
from luxury_fashion.apps.website.services.campaign_service import (
    activate_campaign_for_admin,
    create_campaign_for_admin,
    deactivate_campaign_for_admin,
    delete_campaign_for_admin,
    get_campaign_for_all,
    list_campaigns_queryset,
    list_running_campaigns_for_all,
    update_campaign_for_admin,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Público (leitura)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    response={200: PageOut[CampaignOut]},
    auth=None,
    summary="Lista campanhas (paginado)",
    description="Uso público: por padrão retorna só campanhas ativas. Admin pode ver todas com active_only=false.",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_campaigns_router(request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT, active_only: bool = True):
    qs = list_campaigns_queryset(active_only=active_only)
    return 200, paginate_queryset(qs, page, page_size, CampaignOut.from_orm)


@router.get(
    "/running",
    response={200: list[CampaignOut]},
    auth=None,
    summary="Lista campanhas ativas e dentro da janela de vigência",
    description="Uso público (home/vitrine) — ignora campanhas fora do período de starts_at/ends_at.",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_running_campaigns_router(request):
    return 200, list_running_campaigns_for_all()


@router.get(
    "/{campaign_id}",
    response={200: CampaignOut, 404: MessageOut},
    auth=None,
    summary="Detalhe de uma campanha",
)
@ratelimit(key="ip", rate="60/m", block=True)
def detail_campaign_router(request, campaign_id: uuid.UUID):
    try:
        return 200, get_campaign_for_all(campaign_id)
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}


@router.get(
    "/{campaign_id}/images",
    response={200: list[CampaignImageOut]},
    auth=None,
    summary="Lista as imagens/banners de uma campanha",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_campaign_images_router(request, campaign_id: uuid.UUID):
    return 200, list_campaign_images_for_all(campaign_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Escrita (admin)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response={201: CampaignOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cria uma nova campanha",
)
@ratelimit(key="user", rate="30/h", block=True)
def create_campaign_router(request, payload: CampaignCreateIn):
    try:
        return 201, create_campaign_for_admin(payload)
    except CampaignTitleAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.patch(
    "/{campaign_id}",
    response={200: CampaignOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza uma campanha existente",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_campaign_router(request, campaign_id: uuid.UUID, payload: CampaignUpdateIn):
    try:
        return 200, update_campaign_for_admin(campaign_id, payload)
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}
    except CampaignTitleAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.delete(
    "/{campaign_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma campanha",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_campaign_router(request, campaign_id: uuid.UUID):
    try:
        delete_campaign_for_admin(campaign_id)
        return 200, {"detail": "Campanha excluída com sucesso."}
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{campaign_id}/activate",
    response={200: CampaignOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Ativa uma campanha",
)
@ratelimit(key="user", rate="30/h", block=True)
def activate_campaign_router(request, campaign_id: uuid.UUID):
    try:
        return 200, activate_campaign_for_admin(campaign_id)
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{campaign_id}/deactivate",
    response={200: CampaignOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Desativa uma campanha",
)
@ratelimit(key="user", rate="30/h", block=True)
def deactivate_campaign_router(request, campaign_id: uuid.UUID):
    try:
        return 200, deactivate_campaign_for_admin(campaign_id)
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Imagens/banners (admin)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{campaign_id}/images",
    response={201: CampaignImageOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Faz upload de uma imagem/banner para a campanha",
)
@ratelimit(key="user", rate="20/h", block=True)
def upload_campaign_image_router(
    request,
    campaign_id: uuid.UUID,
    image: UploadedFile = File(...),
    is_cover: bool = False,
    display_order: int = 0,
):
    try:
        return 201, upload_campaign_image_for_admin(campaign_id, image, is_cover, display_order)
    except CampaignNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/images/{campaign_mage_id}",
    response={200: CampaignImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza metadados de uma imagem da campanha (capa/ordem)",
)
@ratelimit(key="user", rate="30/h", block=True)
def update_campaign_image_router(request, campaign_mage_id: uuid.UUID, payload: CampaignImageUpdateIn):
    try:
        return 200, update_campaign_image_for_admin(campaign_mage_id, payload)
    except CampaignImageNotFound as e:
        return 404, {"detail": str(e)}


@router.delete(
    "/images/{campaign_mage_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Exclui uma imagem da campanha",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_campaign_image_router(request, campaign_mage_id: uuid.UUID):
    try:
        delete_campaign_image_for_admin(campaign_mage_id)
        return 200, {"detail": "Imagem excluída com sucesso."}
    except CampaignImageNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/images/{campaign_mage_id}/set-cover",
    response={200: CampaignImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Define a imagem como capa da campanha",
)
@ratelimit(key="user", rate="30/h", block=True)
def set_cover_campaign_image_router(request, campaign_mage_id: uuid.UUID):
    try:
        return 200, set_cover_campaign_image_for_admin(campaign_mage_id)
    except CampaignImageNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/images/{campaign_mage_id}/reorder",
    response={200: CampaignImageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Reordena a imagem da campanha",
)
@ratelimit(key="user", rate="30/h", block=True)
def reorder_campaign_image_router(request, campaign_mage_id: uuid.UUID, display_order: int):
    try:
        return 200, reorder_campaign_image_for_admin(campaign_mage_id, display_order)
    except CampaignImageNotFound as e:
        return 404, {"detail": str(e)}