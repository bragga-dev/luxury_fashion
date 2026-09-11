"""
Admin Profile Services — atualização do perfil (nome completo + foto)
do usuário ADMIN logado.
"""
import uuid

from ninja import UploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.repositories.admin_repository import (
    set_admin_photo,
    remove_admin_photo,
    update_admin_profile as update_admin_profile_repo,
)
from luxury_fashion.apps.accounts.schemas.admin_schema import AdminProfileOut, AdminProfileUpdateIn
from luxury_fashion.apps.accounts.selectors.admin_selector import get_admin_profile_by_user_id
from luxury_fashion.apps.accounts.selectors.user_selector import get_user_with_related
from luxury_fashion.apps.core.exceptions.user import UserNotFound
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.exceptions.media import InvalidImageFile
from luxury_fashion.apps.core.validators.image_validator import validate_image_file


def update_admin_profile(user_id: uuid.UUID, payload: AdminProfileUpdateIn) -> AdminProfileOut:
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    if user.role != User.UserRole.ADMIN:
        raise PermissionDenied("Apenas administradores podem atualizar este perfil.")

    admin_profile = getattr(user, "admin_profile", None)
    if not admin_profile:
        raise UserNotFound("Perfil de administrador não encontrado.")

    fields = payload.dict(exclude_unset=True)
    updated = update_admin_profile_repo(admin_profile=admin_profile, **fields)
    return AdminProfileOut.from_orm(updated)


def upload_admin_profile_photo(user_id: uuid.UUID, photo: UploadedFile) -> AdminProfileOut:
    admin_profile = get_admin_profile_by_user_id(user_id=user_id)
    if not admin_profile:
        raise UserNotFound("Perfil de administrador não encontrado.")

    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))

    updated = set_admin_photo(admin_profile=admin_profile, photo=photo)
    return AdminProfileOut.from_orm(updated)


def delete_admin_profile_photo(user_id: uuid.UUID) -> AdminProfileOut:
    admin_profile = get_admin_profile_by_user_id(user_id=user_id)
    if not admin_profile:
        raise UserNotFound("Perfil de administrador não encontrado.")

    updated = remove_admin_photo(admin_profile=admin_profile)
    return AdminProfileOut.from_orm(updated)