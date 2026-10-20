"""Testes dos guards de permissão (core/permissions/guards.py). Sem banco: usuários em memória."""
from types import SimpleNamespace

import pytest

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.schemas.user_schema import UserRoleEnum
from luxury_fashion.apps.core.exceptions import PermissionDenied
from luxury_fashion.apps.core.permissions import guards
from luxury_fashion.apps.core.permissions.guards import (
    api_guard,
    check_object_permission,
    check_permission,
    guard,
    guard_multiple,
    require_active,
    require_admin,
    require_client,
    require_client_or_admin,
    require_owner_or_admin,
    require_role,
    require_staff,
    require_verified,
    require_verified_client,
)


def make_user(role=User.UserRole.CLIENT, *, active=True, trusty=True, staff=False, superuser=False) -> User:
    return User(
        email=f"{role}@example.com",
        role=role,
        is_active=active,
        is_trusty=trusty,
        is_staff=staff,
        is_superuser=superuser,
    )


@pytest.fixture
def client_ok():
    return make_user()


@pytest.fixture
def admin():
    return make_user(User.UserRole.ADMIN)


@pytest.fixture
def superuser():
    return make_user(User.UserRole.CLIENT, superuser=True)


# ── check_permission / check_object_permission ────────────────────────────────

class TestCheckPermission:
    def test_passa_quando_todas_as_checagens_passam(self, client_ok):
        check_permission(client_ok, lambda u: True, lambda u: True)

    def test_falha_na_primeira_checagem_que_nao_passa(self, client_ok):
        with pytest.raises(PermissionDenied):
            check_permission(client_ok, lambda u: True, lambda u: False)

    def test_mensagem_padrao_cita_a_checagem_que_falhou(self, client_ok):
        def minha_regra(u):
            return False

        with pytest.raises(PermissionDenied, match="minha_regra"):
            check_permission(client_ok, minha_regra)

    def test_mensagem_customizada(self, client_ok):
        with pytest.raises(PermissionDenied, match="sem acesso"):
            check_permission(client_ok, lambda u: False, message="sem acesso")

    def test_admin_ignora_as_checagens(self, admin):
        check_permission(admin, lambda u: False)

    def test_superuser_ignora_as_checagens(self, superuser):
        check_permission(superuser, lambda u: False)

    def test_admin_sem_bypass_e_checado(self, admin):
        with pytest.raises(PermissionDenied):
            check_permission(admin, lambda u: False, allow_admin_bypass=False)

    def test_sem_checagens_nao_levanta(self, client_ok):
        check_permission(client_ok)


class TestCheckObjectPermission:
    def test_passa_com_objeto(self, client_ok):
        obj = object()
        check_object_permission(client_ok, obj, lambda u, o: o is obj)

    def test_falha_com_objeto(self, client_ok):
        with pytest.raises(PermissionDenied):
            check_object_permission(client_ok, object(), lambda u, o: False)

    def test_mensagem_customizada(self, client_ok):
        with pytest.raises(PermissionDenied, match="não é seu"):
            check_object_permission(client_ok, object(), lambda u, o: False, message="não é seu")

    def test_admin_ignora(self, admin):
        check_object_permission(admin, object(), lambda u, o: False)

    def test_admin_sem_bypass_e_checado(self, admin):
        with pytest.raises(PermissionDenied):
            check_object_permission(admin, object(), lambda u, o: False, allow_admin_bypass=False)


# ── guards específicos ────────────────────────────────────────────────────────

class TestRequireActive:
    def test_ativo_passa(self, client_ok):
        require_active(client_ok)

    def test_inativo_levanta(self):
        with pytest.raises(PermissionDenied, match="não está ativa"):
            require_active(make_user(active=False))

    def test_admin_inativo_passa(self):
        require_active(make_user(User.UserRole.ADMIN, active=False))


class TestRequireVerified:
    def test_verificado_passa(self, client_ok):
        require_verified(client_ok)

    def test_nao_trusty_levanta(self):
        with pytest.raises(PermissionDenied, match="Verifique seu e-mail"):
            require_verified(make_user(trusty=False))

    def test_inativo_levanta(self):
        with pytest.raises(PermissionDenied):
            require_verified(make_user(active=False))

    def test_admin_nao_verificado_passa(self):
        require_verified(make_user(User.UserRole.ADMIN, trusty=False))


class TestRequireStaff:
    def test_staff_passa(self):
        require_staff(make_user(staff=True))

    def test_nao_staff_levanta(self, client_ok):
        with pytest.raises(PermissionDenied, match="equipe administrativa"):
            require_staff(client_ok)

    def test_admin_sem_flag_staff_passa(self, admin):
        require_staff(admin)


class TestRequireClientOrAdmin:
    def test_cliente_passa(self, client_ok):
        require_client_or_admin(client_ok)

    def test_admin_passa(self, admin):
        require_client_or_admin(admin)

    def test_role_desconhecida_levanta(self):
        with pytest.raises(PermissionDenied, match="clientes"):
            require_client_or_admin(make_user(role="visitante"))


class TestRequireVerifiedClient:
    def test_cliente_verificado_passa(self, client_ok):
        require_verified_client(client_ok)

    def test_cliente_nao_verificado_levanta(self):
        with pytest.raises(PermissionDenied, match="clientes verificados"):
            require_verified_client(make_user(trusty=False))

    def test_nao_cliente_levanta(self):
        with pytest.raises(PermissionDenied, match="clientes verificados"):
            require_verified_client(make_user(role="visitante"))

    def test_admin_passa(self, admin):
        require_verified_client(admin)


# ── factory require_role ──────────────────────────────────────────────────────

class TestRequireRole:
    def test_role_correta_passa(self, client_ok):
        require_client(client_ok)

    def test_role_errada_levanta_com_mensagem_padrao(self):
        with pytest.raises(PermissionDenied, match="Acesso restrito a admins"):
            require_admin(make_user(role="visitante"))

    def test_cliente_nao_passa_em_require_admin(self, client_ok):
        with pytest.raises(PermissionDenied):
            require_admin(client_ok)

    def test_admin_passa_em_qualquer_role(self, admin):
        require_client(admin)
        require_role("qualquer-coisa")(admin)

    def test_superuser_passa_em_qualquer_role(self, superuser):
        require_admin(superuser)

    def test_aceita_enum(self, client_ok):
        require_role(UserRoleEnum.CLIENT)(client_ok)

    def test_enum_com_role_errada_levanta(self):
        with pytest.raises(PermissionDenied):
            require_role(UserRoleEnum.CLIENT)(make_user(role="visitante"))

    def test_mensagem_customizada(self):
        with pytest.raises(PermissionDenied, match="só lojista"):
            require_role("lojista", custom_message="só lojista")(make_user())


# ── guard compostos ───────────────────────────────────────────────────────────

class TestRequireOwnerOrAdmin:
    def test_dono_passa(self, client_ok):
        require_owner_or_admin(client_ok, object(), lambda u, o: True)

    def test_nao_dono_levanta(self, client_ok):
        with pytest.raises(PermissionDenied, match="permissão para acessar"):
            require_owner_or_admin(client_ok, object(), lambda u, o: False)

    def test_admin_passa_mesmo_sem_ser_dono(self, admin):
        require_owner_or_admin(admin, object(), lambda u, o: False)


# ── decorators ────────────────────────────────────────────────────────────────

def make_request(user):
    return SimpleNamespace(user=user)


@pytest.mark.parametrize("decorator", [guard, api_guard])
class TestGuardDecorators:
    def test_executa_a_view_quando_permitido(self, decorator, client_ok):
        @decorator(require_active)
        def view(request, x, y=0):
            return x + y

        assert view(make_request(client_ok), 1, y=2) == 3

    def test_bloqueia_antes_de_executar_a_view(self, decorator):
        chamadas = []

        @decorator(require_active)
        def view(request):
            chamadas.append(1)

        with pytest.raises(PermissionDenied):
            view(make_request(make_user(active=False)))
        assert chamadas == []

    def test_preserva_metadados_da_view(self, decorator):
        @decorator(require_active)
        def minha_view(request):
            """doc"""

        assert minha_view.__name__ == "minha_view" and minha_view.__doc__ == "doc"


class TestGuardMultiple:
    def test_passa_quando_todos_passam(self, client_ok):
        @guard_multiple(require_active, require_verified, require_client)
        def view(request):
            return "ok"

        assert view(make_request(client_ok)) == "ok"

    def test_bloqueia_se_qualquer_um_falhar(self):
        @guard_multiple(require_active, require_verified)
        def view(request):
            return "ok"

        with pytest.raises(PermissionDenied, match="Verifique seu e-mail"):
            view(make_request(make_user(trusty=False)))

    def test_para_no_primeiro_que_falha(self):
        ordem = []

        def primeiro(user):
            ordem.append("primeiro")
            raise PermissionDenied("x")

        def segundo(user):
            ordem.append("segundo")

        @guard_multiple(primeiro, segundo)
        def view(request):
            return "ok"

        with pytest.raises(PermissionDenied):
            view(make_request(make_user()))
        assert ordem == ["primeiro"]


def test_guards_exportados():
    assert guards.require_client is require_client
    assert guards.require_admin is require_admin