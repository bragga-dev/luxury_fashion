"""Testes de integração da API REST do chat (roteamento, auth, permissões, multipart)."""
import uuid

import pytest

from luxury_fashion.apps.chat.models.message_model import Message
from luxury_fashion.apps.chat.services.message_service import send_message

from .conftest import auth_header

pytestmark = pytest.mark.django_db

BASE = "/api/chat/conversations"


def post_json(client, url, user, data=None):
    return client.post(url, data=data or {}, content_type="application/json", **auth_header(user))


class TestStartConversation:
    def test_cliente_abre_conversa(self, client, client_user):
        resp = post_json(client, BASE, client_user)
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["status"] == "open"
        assert body["client_id"] == str(client_user.user_id)

    def test_retoma_a_mesma_conversa(self, client, client_user):
        a = post_json(client, BASE, client_user).json()
        b = post_json(client, BASE, client_user).json()
        assert a["conversation_id"] == b["conversation_id"]

    def test_exige_autenticacao(self, client):
        assert client.post(BASE, data={}, content_type="application/json").status_code == 401

    def test_usuario_nao_verificado_recebe_403(self, client, db):
        from luxury_fashion.apps.accounts.models.user_model import User

        u = User.objects.create_user(email="nv@example.com", password="x-senha-123456", is_active=True, is_trusty=False)
        assert post_json(client, BASE, u).status_code == 403


class TestListAndDetail:
    def test_lista_minhas(self, client, client_user, other_client, conversation):
        from luxury_fashion.apps.chat.models.conversation_model import Conversation

        Conversation.objects.create(client=other_client)
        resp = client.get(f"{BASE}/mine", **auth_header(client_user))
        assert resp.status_code == 200
        assert [c["conversation_id"] for c in resp.json()] == [str(conversation.conversation_id)]

    def test_inbox_admin_so_para_admin(self, client, client_user, admin_user, conversation):
        assert client.get(f"{BASE}/admin", **auth_header(client_user)).status_code == 403
        resp = client.get(f"{BASE}/admin", **auth_header(admin_user))
        assert resp.status_code == 200 and len(resp.json()) == 1

    def test_inbox_filtra_por_status(self, client, admin_user, conversation):
        assert len(client.get(f"{BASE}/admin?status=closed", **auth_header(admin_user)).json()) == 0
        assert len(client.get(f"{BASE}/admin?status=open", **auth_header(admin_user)).json()) == 1

    def test_detalhe_dono_admin_e_estranho(self, client, client_user, other_client, admin_user, conversation):
        url = f"{BASE}/{conversation.conversation_id}"
        assert client.get(url, **auth_header(client_user)).status_code == 200
        assert client.get(url, **auth_header(admin_user)).status_code == 200
        assert client.get(url, **auth_header(other_client)).status_code == 403

    def test_detalhe_inexistente_404(self, client, client_user):
        assert client.get(f"{BASE}/{uuid.uuid4()}", **auth_header(client_user)).status_code == 404


class TestMessagesEndpoint:
    def url(self, conversation):
        return f"{BASE}/{conversation.conversation_id}/messages"

    def test_envia_texto_multipart(self, client, client_user, conversation):
        resp = client.post(self.url(conversation), data={"content": "oi loja"}, **auth_header(client_user))
        assert resp.status_code == 201, resp.content
        assert resp.json()["content"] == "oi loja"

    def test_envia_com_anexo(self, client, client_user, conversation, chat_storage, png_file):
        resp = client.post(
            self.url(conversation), data={"content": "defeito", "files": png_file}, **auth_header(client_user)
        )
        assert resp.status_code == 201, resp.content
        att = resp.json()["attachments"]
        assert len(att) == 1 and att[0]["file_type"] == "image"

    def test_vazia_retorna_400(self, client, client_user, conversation):
        resp = client.post(self.url(conversation), data={"content": "  "}, **auth_header(client_user))
        assert resp.status_code == 400

    def test_mais_de_5_anexos_retorna_400(self, client, client_user, conversation, chat_storage):
        from django.core.files.uploadedfile import SimpleUploadedFile

        files = [SimpleUploadedFile(f"n{i}.txt", b"x") for i in range(6)]
        resp = client.post(self.url(conversation), data={"content": "", "files": files}, **auth_header(client_user))
        assert resp.status_code == 400

    def test_estranho_retorna_403_e_nada_e_gravado(self, client, other_client, conversation):
        resp = client.post(self.url(conversation), data={"content": "invasão"}, **auth_header(other_client))
        assert resp.status_code == 403
        assert Message.objects.count() == 0

    def test_conversa_inexistente_404(self, client, client_user):
        resp = client.post(f"{BASE}/{uuid.uuid4()}/messages", data={"content": "oi"}, **auth_header(client_user))
        assert resp.status_code == 404

    def test_historico(self, client, client_user, admin_user, conversation):
        send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="a")
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="b")
        resp = client.get(self.url(conversation), **auth_header(client_user))
        assert resp.status_code == 200
        assert [m["content"] for m in resp.json()] == ["a", "b"]

    def test_historico_de_estranho_403(self, client, other_client, conversation):
        assert client.get(self.url(conversation), **auth_header(other_client)).status_code == 403


class TestReadEndpoint:
    def test_marca_como_lida(self, client, client_user, admin_user, conversation):
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="oi")
        resp = post_json(client, f"{BASE}/{conversation.conversation_id}/read", client_user)
        assert resp.status_code == 200
        assert resp.json() == {"updated": 1}

    def test_estranho_403(self, client, other_client, conversation):
        assert post_json(client, f"{BASE}/{conversation.conversation_id}/read", other_client).status_code == 403