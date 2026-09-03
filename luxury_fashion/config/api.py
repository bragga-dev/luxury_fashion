from ninja import NinjaAPI, Swagger
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import AuthenticationFailed as JWTAuthenticationFailed
from ninja.errors import ValidationError, AuthenticationError
from django.http import HttpRequest
from django.http import JsonResponse
from luxury_fashion.apps.core.exceptions import PermissionDenied
from luxury_fashion.apps.accounts.api.auth import router as auth_router
from luxury_fashion.apps.accounts.api.admin import router as admin_router
from luxury_fashion.apps.products.api.category import router as category_router
from luxury_fashion.apps.products.api.product import router as product_router
from luxury_fashion.apps.products.api.frenet import router as frenet_router
from luxury_fashion.apps.accounts.api.address import router as address_router


from django_ratelimit.exceptions import Ratelimited
import logging
from django.conf import settings
logger = logging.getLogger("django")


from luxury_fashion.apps.core.permissions.auth_classes import (
    AdminOnlyAuth,
    ClientOnlyAuth,
    VerifiedUserAuth,
    ActiveUserAuth,
)

api = NinjaAPI(
    title="ÉLUXO MODAS API",
    version="1.0.0",
    description="E-commerce de moda masculina e feminina.",
    auth=[JWTAuth(), AdminOnlyAuth(), ClientOnlyAuth(), VerifiedUserAuth(), ActiveUserAuth()],
    urls_namespace="api",
    docs=Swagger(settings={"persistAuthorization": True}),
)


# ── Routers ───────────────────────────────────────────────────────────────────


api.add_router("/auth/", auth_router, tags=["Auth"])
api.add_router("/admin/", admin_router, tags=["Admin"])
api.add_router("/categories/", category_router, tags=["Categorias"])
api.add_router("/products/", product_router, tags=["Produtos"])
api.add_router("/shipping/", frenet_router, tags=["Shipping"])
api.add_router("/address/", address_router, tags=["Address"])

# ── Handlers de erro globais ──────────────────────────────────────────────────

@api.exception_handler(ValidationError)
def validation_error(request: HttpRequest, exc: ValidationError):
    return api.create_response(
        request,
        {"detail": exc.errors},
        status=422,
    )


@api.exception_handler(AuthenticationError)
def auth_error(request: HttpRequest, exc: AuthenticationError):
    return JsonResponse(
        {"detail": "Credenciais inválidas ou token expirado."},
        status=401,
    )


@api.exception_handler(JWTAuthenticationFailed)
def jwt_authentication_failed(request: HttpRequest, exc: JWTAuthenticationFailed):
    detail = exc.args[0] if exc.args else {}
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    return api.create_response(
        request,
        {"detail": str(message)},
        status=401,
    )


@api.exception_handler(PermissionDenied)
def permission_denied(request: HttpRequest, exc: PermissionDenied):
    return api.create_response(
        request,
        {"detail": str(exc)},
        status=403,
    )


@api.exception_handler(Ratelimited)
def ratelimit_error(request: HttpRequest, exc: Ratelimited):
    return api.create_response(request, {"detail": f"Muitas tentativas. Tente novamente mais tarde."}, status=429,)


@api.exception_handler(Exception)
def internal_server_error(request: HttpRequest, exc: Exception):
    logger.exception("Erro não tratado na API: %s", exc)

    payload = {"detail": "Erro interno do servidor."}

    if settings.DEBUG:
        payload["exception"] = str(exc)

    return api.create_response(
        request,
        payload,
        status=500,
    )