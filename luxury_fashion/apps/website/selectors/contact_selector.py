"""
Contact Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from luxury_fashion.apps.website.models.contact_model import Contact


def get_contact_by_id(contact_id: uuid.UUID) -> Optional[Contact]:
    return Contact.objects.filter(contact_id=contact_id).first()


def contact_name_exists(full_name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    qs = Contact.objects.filter(full_name__iexact=full_name)
    if exclude_id:
        qs = qs.exclude(contact_id=exclude_id)
    return qs.exists()


def get_all_contacts(
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> QuerySet[Contact]:
    qs = Contact.objects.all()

    if status:
        qs = qs.filter(status=status)

    if search:
        qs = qs.filter(
            Q(full_name__icontains=search) | Q(email__icontains=search) | Q(subject__icontains=search)
        )

    return qs.order_by("-created_at")