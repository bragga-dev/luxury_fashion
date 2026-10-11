"""Rotas de embalagem (peso/dimensões) da variante — uso administrativo."""
from decimal import Decimal

import pytest
from ninja_jwt.tokens import RefreshToken

from luxury_fashion.apps.accounts.models.user_model import User

pytestmark = pytest.mark.django_db

BODY = {"weight": "0.4", "height": "6", "width": "13", "length": "17", "quantity": 1}


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _cep_sem_rede(monkeypatch):
    """O model valida o CEP de origem consultando o brazilcep; nos testes não sai pra internet."""
    monkeypatch.setattr("brazilcep.get_address_from_cep", lambda cep, *a, **k: {"cep": cep})


@pytest.fixture
def admin(db) -> User:
    return User.objects.create_superuser(email="admin@example.com", password="senha-super-segura-123")


def url(variant) -> str:
    return f"/api/products/variants/{variant.variant_id}/shipping"


def test_get_sem_embalagem_da_404(client, admin, variant):
    assert client.get(url(variant), **auth_header(admin)).status_code == 404


def test_cria_consulta_e_atualiza_embalagem(client, admin, variant):
    resp = client.post(url(variant), data=BODY, content_type="application/json", **auth_header(admin))
    assert resp.status_code == 201, resp.content

    resp = client.get(url(variant), **auth_header(admin))
    assert resp.status_code == 200
    assert Decimal(resp.json()["weight"]) == Decimal("0.4")

    resp = client.patch(url(variant), data={"weight": "0.9"}, content_type="application/json", **auth_header(admin))
    assert resp.status_code == 200, resp.content
    assert Decimal(resp.json()["weight"]) == Decimal("0.9")
    assert Decimal(resp.json()["height"]) == Decimal("6")  # campo não enviado fica como estava


def test_criar_duas_vezes_da_409(client, admin, variant):
    client.post(url(variant), data=BODY, content_type="application/json", **auth_header(admin))
    resp = client.post(url(variant), data=BODY, content_type="application/json", **auth_header(admin))
    assert resp.status_code == 409


def test_patch_sem_embalagem_da_404(client, admin, variant):
    resp = client.patch(url(variant), data={"weight": "1"}, content_type="application/json", **auth_header(admin))
    assert resp.status_code == 404


def test_cliente_comum_nao_acessa(client, user, variant):
    resp = client.get(url(variant), **auth_header(user))
    assert resp.status_code == 403