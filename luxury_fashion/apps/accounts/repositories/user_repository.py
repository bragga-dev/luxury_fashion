"""
User Repository — persistência de User.
"""
from django.utils import timezone
from typing import Optional
from luxury_fashion.apps.accounts.models.user_model import User


def create_user(*, email: str, password: Optional[str], role: str,
) -> User:
    """
    Cria o usuário base. Se password for None (ex.: cadastro via Google),
    o Django automaticamente marca a senha como "unusable" — o usuário
    não conseguirá logar com email/senha, apenas via provedor OAuth.
    """
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
    )
    return user

def activate_user(user: User) -> User:
    if not user.is_active or not user.is_trusty:
        user.is_active = True
        user.is_trusty = True
        user.save(update_fields=["is_active", "is_trusty"])
    return user

def deactivate_user(user: User) -> User:
    if user.is_active or user.is_trusty:
        user.is_active = False
        user.is_trusty = False
        user.save(update_fields=["is_active", "is_trusty"])
    return user


def delete_user(user: User) -> None:
    user.delete()


def record_terms_acceptance(user: User, *, terms_version: str, privacy_version: str, ip: Optional[str] = None) -> User:
    user.terms_accepted_at = timezone.now()
    user.terms_version = terms_version
    user.privacy_version = privacy_version
    user.consent_ip = ip or None
    user.save(update_fields=["terms_accepted_at", "terms_version", "privacy_version", "consent_ip"])
    return user


def set_marketing_opt_in(user: User, value: bool) -> User:
    user.marketing_opt_in = value
    user.marketing_opt_in_at = timezone.now()
    user.save(update_fields=["marketing_opt_in", "marketing_opt_in_at"])
    return user