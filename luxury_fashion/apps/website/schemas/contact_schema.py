import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from ninja import Schema
from pydantic import EmailStr, field_validator

from luxury_fashion.apps.website.models.contact_model import Contact


class ContactStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


def _not_blank(v: str, field_label: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError(f"{field_label} não pode ser vazio.")
    return v


class ContactCreateIn(Schema):
    """
    Formulário público de contato — `status` nunca vem do payload, nasce
    sempre como PENDING (definido no service).
    """
    full_name: str
    subject: str
    message: str
    email: EmailStr
    phone: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return _not_blank(v, "Nome completo")

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        return _not_blank(v, "Assunto")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _not_blank(v, "Mensagem")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _not_blank(v, "Telefone")


class ContactUpdateIn(Schema):
    """[Admin] Atualiza o status de moderação do contato."""
    status: ContactStatusEnum


class ContactOut(Schema):
    contact_id: uuid.UUID
    full_name: str
    subject: str
    message: str
    email: str
    phone: str
    status: ContactStatusEnum
    status_label: str
    created_at: datetime

    @classmethod
    def from_orm(cls, contact: Contact) -> "ContactOut":
        return cls(
            contact_id=contact.contact_id,
            full_name=contact.full_name,
            subject=contact.subject,
            message=contact.message,
            email=contact.email,
            phone=contact.phone,
            status=contact.status,
            status_label=contact.get_status_display(),
            created_at=contact.created_at,
        )


class ContactListOut(Schema):
    items: list[ContactOut]