"""Health checks: liveness sempre 200; readiness reflete banco/cache e nunca vaza detalhe de erro."""
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db

HEALTH = "luxury_fashion.apps.core.health"


class TestLive:
    def test_returns_200_without_authentication(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_head_is_allowed_and_post_is_not(self, client):
        assert client.head("/health/live").status_code == 200
        assert client.post("/health/live").status_code == 405

    def test_response_is_never_cached(self, client):
        cache_control = client.get("/health/live")["Cache-Control"]
        assert "no-store" in cache_control and "no-cache" in cache_control


class TestReady:
    def test_ok_when_database_and_cache_work(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "checks": {"database": "ok", "cache": "ok"}}

    def test_503_when_database_is_down(self, client):
        with patch(f"{HEALTH}._check_database", return_value=False):
            resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json() == {"status": "degraded", "checks": {"database": "fail", "cache": "ok"}}

    def test_503_when_cache_is_down(self, client):
        with patch(f"{HEALTH}._check_cache", return_value=False):
            resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["checks"] == {"database": "ok", "cache": "fail"}

    def test_does_not_leak_error_details(self, client):
        boom = Exception("postgres://user:senha-super-secreta@db-interno:5432/loja")
        with patch(f"{HEALTH}.connection.cursor", side_effect=boom), patch(f"{HEALTH}.logger"):
            resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert "senha-super-secreta" not in resp.content.decode()
        assert "db-interno" not in resp.content.decode()

    def test_failure_is_logged(self, client):
        with patch(f"{HEALTH}.connection.cursor", side_effect=Exception("x")), patch(f"{HEALTH}.logger") as log:
            client.get("/health/ready")
        log.exception.assert_called_once()