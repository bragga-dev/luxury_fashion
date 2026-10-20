"""
Autenticação JWT pro handshake do WebSocket.

O navegador não deixa mandar header `Authorization` num WebSocket nativo
(`new WebSocket(url)` só aceita URL + subprotocolos), então o access
token vai na query string da conexão:

    wss://seu-dominio/ws/chat/<conversation_id>/?token=<access_token>

Reaproveita a MESMA validação de token usada nas rotas HTTP
(`ninja_jwt.authentication.JWTBaseAuthentication`) — não reinventa
verificação de assinatura/expiração aqui.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from ninja_jwt.authentication import JWTBaseAuthentication
from ninja_jwt.exceptions import AuthenticationFailed, InvalidToken, TokenError


@database_sync_to_async
def _get_user_from_token(token: str):
    try:
        auth = JWTBaseAuthentication()
        validated_token = auth.get_validated_token(token)
        return auth.get_user(validated_token)
    except (TokenError, InvalidToken, AuthenticationFailed):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]

        scope["user"] = await _get_user_from_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)