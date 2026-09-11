"""
Contact endpoints — envio público do formulário de contato e
moderação/gestão pelo admin.
"""
import uuid
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from luxury_fashion.apps.core.exceptions import ContactNameAlreadyExists, ContactNotFound
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.website.schemas.contact_schema import (
    ContactCreateIn,
    ContactOut,
    ContactStatusEnum,
    ContactUpdateIn,
)
from luxury_fashion.apps.website.services.contact_service import (
    create_contact_message,
    delete_contact_for_admin,
    get_contact_for_admin,
    list_contacts_queryset,
    update_contact_status_for_admin,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Público
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response={201: ContactOut, 400: MessageOut, 409: MessageOut},
    auth=None,
    summary="Envia uma mensagem pelo formulário de contato",
)
@ratelimit(key="ip", rate="5/m", block=True)
def create_contact_router(request, payload: ContactCreateIn):
    try:
        return 201, create_contact_message(payload)
    except ContactNameAlreadyExists as e:
        return 409, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    response={200: PageOut[ContactOut]},
    auth=AdminOnlyAuth(),
    summary="[Admin] Lista mensagens de contato (paginado, filtrável)",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_contacts_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    status: Optional[ContactStatusEnum] = None,
    search: Optional[str] = None,
):
    qs = list_contacts_queryset(status=status.value if status else None, search=search)
    return 200, paginate_queryset(qs, page, page_size, ContactOut.from_orm)


@router.get(
    "/{contact_id}",
    response={200: ContactOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Detalhe de uma mensagem de contato",
)
@ratelimit(key="user", rate="60/m", block=True)
def detail_contact_router(request, contact_id: uuid.UUID):
    try:
        return 200, get_contact_for_admin(contact_id)
    except ContactNotFound as e:
        return 404, {"detail": str(e)}


@router.patch(
    "/{contact_id}",
    response={200: ContactOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Atualiza o status de uma mensagem de contato",
)
@ratelimit(key="user", rate="60/m", block=True)
def update_contact_router(request, contact_id: uuid.UUID, payload: ContactUpdateIn):
    try:
        return 200, update_contact_status_for_admin(contact_id, payload.status.value)
    except ContactNotFound as e:
        return 404, {"detail": str(e)}


@router.delete(
    "/{contact_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Exclui uma mensagem de contato",
)
@ratelimit(key="user", rate="20/h", block=True)
def delete_contact_router(request, contact_id: uuid.UUID):
    try:
        delete_contact_for_admin(contact_id)
        return 200, {"detail": "Contato excluído com sucesso."}
    except ContactNotFound as e:
        return 404, {"detail": str(e)}