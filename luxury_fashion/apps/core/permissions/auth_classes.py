"""
Auth Classes - Classes de autenticação com permissões embutidas.
"""
from ninja_jwt.authentication import JWTAuth
from luxury_fashion.apps.core.exceptions import PermissionDenied
from luxury_fashion.apps.core.permissions.roles import (
    has_any_role,
    is_admin,
    is_active,
    is_client,
    is_verified,
)
from luxury_fashion.apps.accounts.models.user_model import User

DEFAULT_CLIENT_PHOTO = "default/client_img.jpg"

class ClientCompleteProfileAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)

        if not user:
            return None
        if not is_admin(user) and not is_client(user):
            raise PermissionDenied("Apenas clientes podem acessar este recurso.")

        client = getattr(user, "cliente_profile", None)
        if not client:
            raise PermissionDenied("Usuário não possui clientes vinculado.")

        required_fields = {
            "Nome": client.first_name,
            "Sobrenome": client.last_name,
            "CPF": client.cpf,
            "Endereço": client.addresses.exists(),
        }

        missing = [field for field, value in required_fields.items() if not value]

        if missing:
            missing_count = len(missing)
            fields_list = ', '.join(missing)
            
            raise PermissionDenied(
                f"Complete seu perfil antes de executar essa ação. "
                f"{missing_count} campo(s) obrigatório(s) faltando: {fields_list}"
            )

        if not is_verified(user):
            raise PermissionDenied("O cliente precisa ser verificado para acessar.")
        return user


class ClientOnlyAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user) and not is_verified(user):  
            raise PermissionDenied("Verifique seu e-mail para acessar.")
        if user and not is_admin(user) and not is_client(user):
            raise PermissionDenied("Apenas clients podem acessar este recurso.")
        return user


class AdminOnlyAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user):
            raise PermissionDenied("Apenas administradores podem acessar este recurso.")
        return user


class ActiveUserAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_active(user):
            raise PermissionDenied("Sua conta não está ativa.")
        return user


class VerifiedUserAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user) and not is_verified(user):
            raise PermissionDenied("Verifique seu e-mail para acessar.")
        return user


# ═══════════════════════════════════════════════════════════════════════════════
# Classes conjuntas (combinações de roles)
# ═══════════════════════════════════════════════════════════════════════════════

class _CombinedRoleAuth(JWTAuth):
    """
    Base para autenticação que libera acesso a uma combinação de roles.

    Subclasses definem:
      - allowed_roles: lista de User.UserRole permitidas
      - denied_message: mensagem retornada quando a role não está na lista

    Se ADMIN estiver entre as roles permitidas, o admin fica dispensado da
    checagem de e-mail verificado (mesmo comportamento de ClientOnlyAuth /
    AdminOnlyAuth já existentes). Se ADMIN não estiver na lista, ele é
    tratado como qualquer outra role fora da lista: acesso negado.
    """
    allowed_roles: list = []
    denied_message: str = "Você não tem permissão para acessar este recurso."

    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None

        admin_is_allowed = User.UserRole.ADMIN in self.allowed_roles
        if not (admin_is_allowed and is_admin(user)) and not is_verified(user):
            raise PermissionDenied("Verifique seu e-mail para acessar.")

        if not has_any_role(user, self.allowed_roles):
            raise PermissionDenied(self.denied_message)

        return user


class AllRolesAuth(_CombinedRoleAuth):
    """Libera acesso para qualquer usuário autenticado e verificado: admin, client."""
    allowed_roles = [User.UserRole.ADMIN, User.UserRole.CLIENT]
    denied_message = "Acesso não permitido para este tipo de usuário."


class AdminOrClientAuth(_CombinedRoleAuth):
    """Libera acesso apenas para administradores e clientes."""
    allowed_roles = [User.UserRole.ADMIN, User.UserRole.CLIENT]
    denied_message = "Apenas administradores ou clientes podem acessar este recurso."

