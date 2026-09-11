"""
Contact Services — orquestra regras de negócio das mensagens do
formulário de contato (repositories + selectors), devolvendo sempre
schemas prontos para a camada de API.
"""

import uuid
from typing import Optional

from luxury_fashion.apps.core.exceptions.contact_exception import (
    ContactNameAlreadyExists,
    ContactNotFound,
)

from luxury_fashion.apps.website.models.contact_model import Contact

from luxury_fashion.apps.website.repositories.contact_repository import (
    create_contact,
    delete_contact,
    update_contact_status,
)

from luxury_fashion.apps.website.schemas.contact_schema import (
    ContactCreateIn,
    ContactOut,
)

from luxury_fashion.apps.website.selectors.contact_selector import (
    contact_name_exists,
    get_all_contacts,
    get_contact_by_id,
)


def _get_contact_or_raise(contact_id: uuid.UUID) -> Contact:
    contact = get_contact_by_id(contact_id)

    if contact is None:
        raise ContactNotFound()

    return contact


# ── Público ──────────────────────────────────────────────────────────────

def create_contact_message(
    data: ContactCreateIn,
) -> ContactOut:
    """
    Cria uma mensagem de contato enviada pelo formulário público.

    Toda mensagem pública nasce com status PENDING.
    O status nunca é aceito pelo payload.
    """

    if contact_name_exists(data.full_name):
        raise ContactNameAlreadyExists()

    contact = create_contact(
        full_name=data.full_name,
        subject=data.subject,
        message=data.message,
        email=data.email,
        phone=data.phone,
        status=Contact.ContactStatus.PENDING,
    )

    return ContactOut.from_orm(contact)


# ── Admin ────────────────────────────────────────────────────────────────

def get_contact_for_admin(
    contact_id: uuid.UUID,
) -> ContactOut:

    contact = _get_contact_or_raise(contact_id)

    return ContactOut.from_orm(contact)


def list_contacts_queryset(
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """QuerySet bruto de contatos, para paginação na camada de router."""

    return get_all_contacts(
        status=status,
        search=search,
    )


def update_contact_status_for_admin(
    contact_id: uuid.UUID,
    status: str,
) -> ContactOut:

    contact = _get_contact_or_raise(contact_id)

    contact = update_contact_status(
        contact,
        status=status,
    )

    return ContactOut.from_orm(contact)


def delete_contact_for_admin(
    contact_id: uuid.UUID,
) -> None:

    contact = _get_contact_or_raise(contact_id)

    delete_contact(contact)