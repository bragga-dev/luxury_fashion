"""
Consumer do WebSocket de chat.

Protocolo (JSON via `receive`):
  Cliente -> servidor:
    {"type": "message", "content": "texto..."}   — envia mensagem de texto
    {"type": "read"}                              — marca a conversa como lida

  Servidor -> cliente (broadcast pro grupo da conversa):
    {"type": "message", "message": {...MessageOut...}}
    {"type": "read", "reader_id": "<uuid>"}
    {"type": "error", "detail": "..."}

Anexo (foto/vídeo/PDF/TXT) NÃO passa por aqui — é upload multipart pela
API REST (`POST /api/chat/conversations/{id}/messages`), que já reaproveita
o mesmo `send_message` e broadcasta pro grupo da mesma forma. O WebSocket é
só pra texto ao vivo + notificação de leitura.
"""
import json
import logging
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from luxury_fashion.apps.chat.selectors.conversation_selector import (
    get_conversation_by_id,
    user_can_access_conversation,
)

logger = logging.getLogger(__name__)

CLOSE_UNAUTHENTICATED = 4401
CLOSE_NOT_FOUND = 4404
CLOSE_FORBIDDEN = 4403


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"

        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        conversation = await database_sync_to_async(get_conversation_by_id)(UUID(self.conversation_id))
        if conversation is None:
            await self.close(code=CLOSE_NOT_FOUND)
            return

        can_access = await database_sync_to_async(user_can_access_conversation)(conversation, self.user)
        if not can_access:
            await self.close(code=CLOSE_FORBIDDEN)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("JSON inválido.")
            return

        event_type = payload.get("type")

        if event_type == "message":
            await self._handle_send_message(payload)
        elif event_type == "read":
            await self._handle_mark_as_read()
        else:
            await self._send_error(f"Tipo de evento desconhecido: {event_type!r}")

    async def _handle_send_message(self, payload: dict):
        from luxury_fashion.apps.chat.services.message_service import send_message

        content = (payload.get("content") or "").strip()
        if not content:
            await self._send_error("Mensagem vazia. Pra enviar anexo, use a API de upload.")
            return

        try:
            await database_sync_to_async(send_message)(
                conversation_id=UUID(self.conversation_id),
                sender_id=self.user.user_id,
                content=content,
            )
        except Exception as e:
            logger.warning("Falha ao enviar mensagem via WS: %s", e)
            await self._send_error(str(getattr(e, "message", e)))

    async def _handle_mark_as_read(self):
        from luxury_fashion.apps.chat.services.message_service import mark_conversation_as_read

        try:
            await database_sync_to_async(mark_conversation_as_read)(
                user_id=self.user.user_id,
                conversation_id=UUID(self.conversation_id),
            )
        except Exception as e:
            logger.warning("Falha ao marcar como lida via WS: %s", e)
            await self._send_error(str(getattr(e, "message", e)))

    async def _send_error(self, detail: str):
        await self.send(text_data=json.dumps({"type": "error", "detail": detail}))

    # ── Handlers de eventos do grupo (vêm de `channel_layer.group_send`) ──
    # O Channels converte "chat.message" -> método `chat_message`, e
    # "chat.read" -> `chat_read`, casando com o `"type"` usado em
    # `message_service.broadcast_message` / `mark_conversation_as_read`.

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", "message": event["message"]}))

    async def chat_read(self, event):
        await self.send(text_data=json.dumps({"type": "read", "reader_id": event["reader_id"]}))