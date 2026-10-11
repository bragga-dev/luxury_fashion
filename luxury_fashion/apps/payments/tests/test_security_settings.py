"""Cookies e configuração de produção."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]  # raiz do repo (onde fica o manage.py)

PROD_ENV = {
    "SECRET_KEY": "x" * 40, "ALLOWED_HOSTS": "api.example.com", "DATABASE_URL": "sqlite:///x.db",
    "CSRF_TRUSTED_ORIGINS": "https://app.example.com", "REDIS_URL": "redis://localhost:6379/1",
    "ADMIN_EMAIL": "a@example.com", "ASAAS_API_KEY": "x", "ASAAS_WEBHOOK_TOKEN": "x",
    "FRENET_API_KEY": "x", "ORIGIN_ZIP_CODE": "45200000",
    "DEBUG": "True",  # simula um .env de prod copiado do dev
}


@pytest.fixture(scope="module")
def prod():
    """Carrega a settings de PRODUÇÃO num processo à parte e devolve os valores efetivos."""
    code = """
import json, django, environ
environ.Env.read_env = staticmethod(lambda *a, **k: None)  # hermético: ignora o .env local
django.setup()
from django.conf import settings
from ninja_jwt.settings import api_settings
from luxury_fashion.config.api import api
print(json.dumps({
  "rotate": api_settings.ROTATE_REFRESH_TOKENS, "blacklist": api_settings.BLACKLIST_AFTER_ROTATION,
  "last_login": api_settings.UPDATE_LAST_LOGIN, "refresh_days": api_settings.REFRESH_TOKEN_LIFETIME.days,
  "validators": len(settings.AUTH_PASSWORD_VALIDATORS), "cookie_secure": settings.COOKIE_SECURE,
  "docs_url": api.docs_url, "openapi_url": api.openapi_url, "debug": settings.DEBUG,
}))
"""
    env = {**os.environ, **PROD_ENV, "DJANGO_SETTINGS_MODULE": "luxury_fashion.config.settings.prod"}
    # o processo de teste já carregou o .env local no os.environ; em produção essas variáveis
    # NÃO existem — é justamente o cenário que queremos validar (default seguro).
    for var in ("COOKIE_SECURE", "COOKIE_SAMESITE", "API_DOCS_ENABLED"):
        env.pop(var, None)
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_prod_mantem_rotacao_e_blacklist_do_refresh(prod):
    assert prod["rotate"] is True
    assert prod["blacklist"] is True
    assert prod["last_login"] is True
    assert prod["refresh_days"] == 7


def test_prod_cookie_do_refresh_e_secure_mesmo_com_debug_no_env(prod):
    assert prod["cookie_secure"] is True


def test_prod_usa_todos_os_validadores_de_senha(prod):
    assert prod["validators"] >= 4


def test_prod_nao_expoe_swagger(prod):
    assert prod["docs_url"] is None
    assert prod["openapi_url"] is None


# ── Origin nos endpoints que usam o cookie ───────────────────────────────

pytestmark_db = pytest.mark.django_db


@pytest.mark.django_db
def test_refresh_de_origem_nao_confiavel_e_recusado(client):
    resp = client.post("/api/auth/refresh", HTTP_ORIGIN="https://evil.example")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_logout_de_origem_nao_confiavel_e_recusado(client, user):
    from ninja_jwt.tokens import RefreshToken
    token = RefreshToken.for_user(user).access_token
    resp = client.post("/api/auth/logout", HTTP_ORIGIN="https://evil.example", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_refresh_de_origem_confiavel_ou_sem_origin_segue_o_fluxo(client, settings):
    settings.CORS_ALLOWED_ORIGINS = ["https://app.example.com"]
    assert client.post("/api/auth/refresh", HTTP_ORIGIN="https://app.example.com").status_code == 401  # sem cookie
    assert client.post("/api/auth/refresh").status_code == 401  # cliente não-browser (sem Origin)