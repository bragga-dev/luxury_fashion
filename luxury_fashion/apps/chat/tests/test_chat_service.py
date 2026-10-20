"""Testes dos services do chat (conversas, mensagens, leitura, anexos, broadcast)."""
import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

from luxury_fashion.apps.chat.models.conversation_model import Conversation
from luxury_fashion.apps.chat.models.message_model import Message
from luxury_fashion.apps.chat.services.conversation_service import (
    get_conversation_for_user,
    list_conversations_for_admin,
    list_conversations_for_client,
    start_or_resume_conversation,
)
from luxury_fashion.apps.chat.services.message_service import (
    list_messages,
    mark_conversation_as_read,
    send_message,
)
from luxury_fashion.apps.core.exceptions import (
    ConversationNotFound,
    EmptyMessage,
    PermissionDenied,
    TooManyAttachments,
)

pytestmark = pytest.mark.django_db


# ───────────────────────── conversas ─────────────────────────

class TestConversations:
    def test_cria_conversa_aberta(self, client_user):
        out = start_or_resume_conversation(client_user_id=client_user.user_id)
        assert out.status == "open"
        assert out.client_id == client_user.user_id
        assert Conversation.objects.count() == 1

    def test_retoma_conversa_aberta_em_vez_de_duplicar(self, client_user):
        a = start_or_resume_conversation(client_user_id=client_user.user_id)
        b = start_or_resume_conversation(client_user_id=client_user.user_id)
        assert a.conversation_id == b.conversation_id
        assert Conversation.objects.count() == 1

    def test_cria_nova_se_a_anterior_foi_encerrada(self, client_user):
        a = start_or_resume_conversation(client_user_id=client_user.user_id)
        Conversation.objects.get(pk=a.conversation_id).close_conversation()
        b = start_or_resume_conversation(client_user_id=client_user.user_id)
        assert a.conversation_id != b.conversation_id

    def test_clientes_diferentes_tem_conversas_diferentes(self, client_user, other_client):
        a = start_or_resume_conversation(client_user_id=client_user.user_id)
        b = start_or_resume_conversation(client_user_id=other_client.user_id)
        assert a.conversation_id != b.conversation_id

    def test_cliente_ve_so_as_proprias(self, client_user, other_client, conversation):
        Conversation.objects.create(client=other_client)
        mine = list_conversations_for_client(client_user_id=client_user.user_id)
        assert [c.conversation_id for c in mine] == [conversation.conversation_id]

    def test_admin_ve_todas_e_filtra_por_status(self, client_user, other_client, conversation):
        closed = Conversation.objects.create(client=other_client)
        closed.close_conversation()
        assert len(list_conversations_for_admin()) == 2
        only_open = list_conversations_for_admin(status="open")
        assert [c.conversation_id for c in only_open] == [conversation.conversation_id]

    def test_detalhe_permissoes(self, client_user, other_client, admin_user, conversation):
        assert get_conversation_for_user(client_user.user_id, conversation.conversation_id)
        assert get_conversation_for_user(admin_user.user_id, conversation.conversation_id)
        with pytest.raises(PermissionDenied):
            get_conversation_for_user(other_client.user_id, conversation.conversation_id)

    def test_detalhe_inexistente(self, client_user):
        with pytest.raises(ConversationNotFound):
            get_conversation_for_user(client_user.user_id, uuid.uuid4())


# ───────────────────────── mensagens ─────────────────────────

class TestSendMessage:
    def test_envia_texto_e_atualiza_last_message_at(self, client_user, conversation):
        out = send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="  oi  ")
        assert out.content == "oi"  # strip
        assert out.sender_id == client_user.user_id
        assert out.is_read is False
        conversation.refresh_from_db()
        assert conversation.last_message_at is not None

    def test_sender_name_cai_para_email_sem_perfil(self, client_user, conversation):
        out = send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="oi")
        assert out.sender_name == "cliente@example.com"

    def test_admin_pode_responder_qualquer_conversa(self, admin_user, conversation):
        out = send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="Olá!")
        assert out.sender_id == admin_user.user_id

    def test_estranho_nao_pode_enviar(self, other_client, conversation):
        with pytest.raises(PermissionDenied):
            send_message(conversation_id=conversation.conversation_id, sender_id=other_client.user_id, content="invasão")
        assert Message.objects.count() == 0

    def test_conversa_inexistente(self, client_user):
        with pytest.raises(ConversationNotFound):
            send_message(conversation_id=uuid.uuid4(), sender_id=client_user.user_id, content="oi")

    @pytest.mark.parametrize("content", ["", "   ", "\n\t"])
    def test_mensagem_vazia_sem_anexo(self, client_user, conversation, content):
        with pytest.raises(EmptyMessage):
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content=content)

    def test_limite_de_anexos(self, client_user, conversation):
        files = [object()] * 6  # a checagem de quantidade vem antes de qualquer leitura do arquivo
        with pytest.raises(TooManyAttachments):
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, files=files)
        assert Message.objects.count() == 0

    def test_historico_em_ordem_e_restrito_aos_participantes(self, client_user, admin_user, other_client, conversation):
        send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="1")
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="2")
        msgs = list_messages(user_id=client_user.user_id, conversation_id=conversation.conversation_id)
        assert [m.content for m in msgs] == ["1", "2"]
        with pytest.raises(PermissionDenied):
            list_messages(user_id=other_client.user_id, conversation_id=conversation.conversation_id)


# ───────────────────────── anexos ─────────────────────────

class TestAttachments:
    def test_imagem_e_texto_sao_salvos_com_tipo_correto(self, client_user, conversation, chat_storage, png_file, txt_file):
        out = send_message(
            conversation_id=conversation.conversation_id,
            sender_id=client_user.user_id,
            content="olha o defeito",
            files=[png_file, txt_file],
        )
        by_name = {a.original_filename: a for a in out.attachments}
        assert by_name["foto.png"].file_type == "image"
        assert by_name["nota.txt"].file_type == "document"
        assert by_name["foto.png"].url.startswith("/private/chat/")

    def test_so_anexo_sem_texto_e_valido(self, client_user, conversation, chat_storage, txt_file):
        out = send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, files=[txt_file])
        assert out.content == ""
        assert len(out.attachments) == 1

    def test_executavel_renomeado_para_pdf_e_barrado(self, client_user, conversation, chat_storage, fake_pdf_exe):
        with pytest.raises(ValidationError):
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, files=[fake_pdf_exe])
        assert Message.objects.count() == 0  # atomic: nada fica pela metade

    def test_extensao_nao_suportada(self, client_user, conversation, chat_storage):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile("malware.exe", b"MZ" + b"\x00" * 32)
        with pytest.raises(ValidationError):
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, files=[f])


# ───────────────────────── leitura ─────────────────────────

class TestMarkAsRead:
    def test_marca_so_as_mensagens_dos_outros(self, client_user, admin_user, conversation):
        send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="minha")
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="a1")
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="a2")

        assert mark_conversation_as_read(user_id=client_user.user_id, conversation_id=conversation.conversation_id) == 2
        assert Message.objects.get(content="minha").is_read is False
        assert Message.objects.filter(sender=admin_user, is_read=True, read_at__isnull=False).count() == 2

    def test_idempotente(self, client_user, admin_user, conversation):
        send_message(conversation_id=conversation.conversation_id, sender_id=admin_user.user_id, content="oi")
        assert mark_conversation_as_read(user_id=client_user.user_id, conversation_id=conversation.conversation_id) == 1
        assert mark_conversation_as_read(user_id=client_user.user_id, conversation_id=conversation.conversation_id) == 0

    def test_estranho_nao_marca(self, other_client, conversation):
        with pytest.raises(PermissionDenied):
            mark_conversation_as_read(user_id=other_client.user_id, conversation_id=conversation.conversation_id)


# ───────────────────────── broadcast ─────────────────────────

class TestBroadcast:
    def test_mensagem_vai_pro_grupo_so_apos_o_commit(self, client_user, conversation, django_capture_on_commit_callbacks):
        layer = get_channel_layer()
        group = f"chat_{conversation.conversation_id}"
        channel = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)(group, channel)

        with django_capture_on_commit_callbacks(execute=True):
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="ao vivo")

        event = async_to_sync(layer.receive)(channel)
        assert event["type"] == "chat.message"
        assert event["message"]["content"] == "ao vivo"
        assert event["message"]["conversation_id"] == str(conversation.conversation_id)

    def test_sem_commit_nao_ha_broadcast(self, client_user, conversation, django_capture_on_commit_callbacks):
        layer = get_channel_layer()
        group = f"chat_{conversation.conversation_id}"
        channel = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)(group, channel)

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            send_message(conversation_id=conversation.conversation_id, sender_id=client_user.user_id, content="x")
        assert len(callbacks) == 1  # agendado, mas não executado → ninguém recebeu ainda