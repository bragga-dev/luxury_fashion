"""
Health checks para orquestração (Docker healthcheck, uptime monitor, load balancer).

- /health/live  → o processo está de pé (não toca em nada externo). Usado pelo healthcheck do container.
- /health/ready → dependências críticas respondem (banco e cache/Redis). 503 se alguma falhar.

Sem autenticação (quem consulta é infraestrutura) e SEM detalhes de erro na resposta: o motivo da
falha vai pro log, nunca pro corpo — evita expor host/driver/credenciais a quem sondar a rota.
"""
import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger("django")


@require_safe
@never_cache
def live(request):
    return JsonResponse({"status": "ok"})


def _check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("Health check: banco de dados indisponível.")
        return False


def _check_cache() -> bool:
    try:
        cache.set("health:ping", "1", timeout=10)
        return cache.get("health:ping") == "1"
    except Exception:
        logger.exception("Health check: cache/Redis indisponível.")
        return False


@require_safe
@never_cache
def ready(request):
    checks = {"database": _check_database(), "cache": _check_cache()}
    healthy = all(checks.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "checks": {name: "ok" if passed else "fail" for name, passed in checks.items()},
        },
        status=200 if healthy else 503,
    )