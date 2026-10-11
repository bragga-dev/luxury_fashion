"""
Admin Repository — persistência do perfil do Administrador.
"""
from typing import Optional
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.models.admin_model import AdminProfile, DEFAULT_ADMIN_PHOTO
from luxury_fashion.apps.core.tasks.media import delete_old_media_file


def create_admin_profile(
    user_id: User,
    full_name: str,
    photo: Optional[File] = None,
) -> AdminProfile:
    fields = {"full_name": full_name}
    if photo is not None:
        fields["photo"] = photo

    admin_profile = AdminProfile(user_id=user_id, **fields)
    admin_profile.save()
    return admin_profile


def get_or_create_admin_profile(user: User) -> AdminProfile:
    """
    Garante que todo usuário com role ADMIN tenha um AdminProfile.

    Cobre o caso de admins promovidos direto no banco/Django admin (ou
    criados antes deste model existir), que nunca passaram pelo comando
    `createsuperuser` customizado — o único lugar que hoje cria o profile.
    Sem isso, update/upload/delete de perfil admin quebravam sempre com
    404 "Perfil de administrador não encontrado." pra esses usuários.
    """
    admin_profile = getattr(user, "admin_profile", None)
    if admin_profile:
        return admin_profile

    default_name = user.email.split("@")[0]
    return create_admin_profile(user_id=user, full_name=default_name)


def update_admin_profile(admin_profile: AdminProfile, **fields) -> AdminProfile:
    for attr, value in fields.items():
        if value is not None:
            setattr(admin_profile, attr, value)
    admin_profile.save()
    return admin_profile


def delete_admin_profile(admin_profile: AdminProfile) -> None:
    admin_profile.delete()


def set_admin_photo(admin_profile: AdminProfile, photo: InMemoryUploadedFile) -> AdminProfile:
    old_name = admin_profile.photo.name if admin_profile.photo and admin_profile.photo.name != DEFAULT_ADMIN_PHOTO else None
    admin_profile.photo = photo
    admin_profile.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return admin_profile


def remove_admin_photo(admin_profile: AdminProfile) -> AdminProfile:
    old_name = admin_profile.photo.name if admin_profile.photo and admin_profile.photo.name != DEFAULT_ADMIN_PHOTO else None
    admin_profile.photo = DEFAULT_ADMIN_PHOTO
    admin_profile.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return admin_profile