"""
Testes do WebSocket (ChatConsumer + JWTAuthMiddleware) com channels.testing.

Sem pytest-asyncio: cada cenário é uma corrotina rodada por `asyncio.run`.
`transaction=True` é necessário porque o consumer acessa o banco em outra thread
(database_sync_to_async) e o broadcast só dispara no commit real.
"""
import asyncio
import json

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from luxury_fashion.apps.chat.consumers import CLOSE_FORBIDDEN, CLOSE_NOT_FOUND, CLOSE_UNAUTHENTICATED
from luxury_fashion.apps.chat.middleware import JWTAuthMiddlewareStack
from luxury_fashion.apps.chat.models.message_model import Message
from luxury_fashion.apps.chat.routing import websocket_urlpatterns

from .conftest import access_token

pytestmark = pytest.mark.django_db(transaction=True)

APP = JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))


def run(coro):
    return asyncio.run(coro)


def communicator(conversation_id, token=None):
    qs = f"?token={token}" if token else ""
    return WebsocketCommunicator(APP, f"/ws/chat/{conversation_id}/{qs}")


async def connect(conversation_id, user):
    # RefreshToken.for_user toca o banco — não pode rodar direto dentro do event loop.
    token = await database_sync_to_async(access_token)(user)
    comm = communicator(conversation_id, token)
    connected, code = await comm.connect()
    assert connected, f"conexão recusada (code={code})"
    return comm


# ───────────────────────── handshake ─────────────────────────

def test_sem_token_e_recusado(conversation):
    async def scenario():
        comm = communicator(conversation.conversation_id)
        connected, code = await comm.connect()
        assert connected is False and code == CLOSE_UNAUTHENTICATED

    run(scenario())


def test_token_invalido_e_recusado(conversation):
    async def scenario():
        comm = communicator(conversation.conversation_id, "token.invalido.aqui")
        connected, code = await comm.connect()
        assert connected is False and code == CLOSE_UNAUTHENTICATED

    run(scenario())


def test_conversa_inexistente(client_user):
    import uuid

    token = access_token(client_user)

    async def scenario():
        comm = communicator(uuid.uuid4(), token)
        connected, code = await comm.connect()
        assert connected is False and code == CLOSE_NOT_FOUND

    run(scenario())


def test_estranho_e_barrado(conversation, other_client):
    token = access_token(other_client)

    async def scenario():
        comm = communicator(conversation.conversation_id, token)
        connected, code = await comm.connect()
        assert connected is False and code == CLOSE_FORBIDDEN

    run(scenario())


def test_dono_e_admin_conectam(conversation, client_user, admin_user):
    async def scenario():
        a = await connect(conversation.conversation_id, client_user)
        b = await connect(conversation.conversation_id, admin_user)
        await a.disconnect()
        await b.disconnect()

    run(scenario())


# ───────────────────────── mensagens ─────────────────────────

def test_mensagem_chega_para_os_dois_lados_e_e_persistida(conversation, client_user, admin_user):
    async def scenario():
        cliente = await connect(conversation.conversation_id, client_user)
        admin = await connect(conversation.conversation_id, admin_user)

        await cliente.send_json_to({"type": "message", "content": "preciso de ajuda"})

        for comm in (cliente, admin):
            evt = await comm.receive_json_from()
            assert evt["type"] == "message"
            assert evt["message"]["content"] == "preciso de ajuda"
            assert evt["message"]["sender_id"] == str(client_user.user_id)

        await cliente.disconnect()
        await admin.disconnect()

    run(scenario())
    assert Message.objects.filter(content="preciso de ajuda").count() == 1


def test_resposta_do_admin_volta_pro_cliente(conversation, client_user, admin_user):
    async def scenario():
        cliente = await connect(conversation.conversation_id, client_user)
        admin = await connect(conversation.conversation_id, admin_user)

        await admin.send_json_to({"type": "message", "content": "já vamos ver"})
        evt = await cliente.receive_json_from()
        assert evt["message"]["sender_id"] == str(admin_user.user_id)
        await admin.receive_json_from()  # eco do próprio admin

        await cliente.disconnect()
        await admin.disconnect()

    run(scenario())


def test_conversas_diferentes_nao_vazam(conversation, client_user, other_client, admin_user):
    from luxury_fashion.apps.chat.models.conversation_model import Conversation

    outra = Conversation.objects.create(client=other_client)

    async def scenario():
        a = await connect(conversation.conversation_id, client_user)
        b = await connect(outra.conversation_id, other_client)

        await a.send_json_to({"type": "message", "content": "segredo da conversa A"})
        await a.receive_json_from()
        assert await b.receive_nothing(timeout=0.3) is True

        await a.disconnect()
        await b.disconnect()

    run(scenario())


# ───────────────────────── leitura ─────────────────────────

def test_evento_read_notifica_o_outro_lado(conversation, client_user, admin_user):
    async def scenario():
        cliente = await connect(conversation.conversation_id, client_user)
        admin = await connect(conversation.conversation_id, admin_user)

        await cliente.send_json_to({"type": "message", "content": "oi"})
        await cliente.receive_json_from()
        await admin.receive_json_from()

        await admin.send_json_to({"type": "read"})
        evt = await cliente.receive_json_from()
        assert evt == {"type": "read", "reader_id": str(admin_user.user_id)}

        await cliente.disconnect()
        await admin.disconnect()

    run(scenario())
    assert Message.objects.get(content="oi").is_read is True


# ───────────────────────── protocolo / erros ─────────────────────────

@pytest.mark.parametrize(
    "raw, trecho",
    [
        ("isso não é json", "JSON inválido"),
        (json.dumps({"type": "foo"}), "desconhecido"),
        (json.dumps({"type": "message", "content": "   "}), "vazia"),
        (json.dumps({"type": "message"}), "vazia"),
    ],
)
def test_erros_de_protocolo_voltam_como_evento_error(conversation, client_user, raw, trecho):
    async def scenario():
        comm = await connect(conversation.conversation_id, client_user)
        await comm.send_to(text_data=raw)
        evt = await comm.receive_json_from()
        assert evt["type"] == "error" and trecho in evt["detail"]
        await comm.disconnect()

    run(scenario())
    assert Message.objects.count() == 0