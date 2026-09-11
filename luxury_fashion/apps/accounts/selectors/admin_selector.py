"""
Admin Selectors — queries de leitura para AdminProfile.
Nenhuma escrita acontece aqui.
"""
from typing import Optional
from uuid import UUID

from luxury_fashion.apps.accounts.models.admin_model import AdminProfile


def get_admin_profile_by_user_id(user_id: UUID) -> Optional[AdminProfile]:
    """Retorna o perfil do administrador pelo ID do usuário associado."""
    try:
        return AdminProfile.objects.get(user_id=user_id)
    except AdminProfile.DoesNotExist:
        return None


def get_admin_profile_by_id(admin_id: UUID) -> Optional[AdminProfile]:
    """Retorna o perfil do administrador pelo próprio ID."""
    try:
        return AdminProfile.objects.get(admin_id=admin_id)
    except AdminProfile.DoesNotExist:
        return None