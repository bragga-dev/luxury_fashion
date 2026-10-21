"""
Chat endpoints (REST) — abrir/listar conversas, histórico, envio de mensagem
com anexo (multipart) e marcação de leitura. Texto puro em tempo real vai
pelo WebSocket; anexo precisa passar por aqui.
"""
import uuid
from typing import List, Optional

from django_ratelimit.decorators import ratelimit
from ninja import File, Form, Router, Schema, Status, UploadedFile

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.chat.schemas.chat_schema import (
    ConversationOut,
    MessageOut,
    StartConversationIn,
)
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
    TooManyAttachments,
    UserNotFound,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth, AllRolesAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut as DetailOut

router = Router()


class ReadOut(Schema):
    updated: int


@router.post(
    "/conversations",
    response={201: ConversationOut, 404: DetailOut},
    auth=AllRolesAuth(),
    summary="Abre (ou retoma) a conversa do cliente",
)
@ratelimit(key="user", rate="30/m", block=True)
def start_conversation_router(request, payload: StartConversationIn):
    user: User = request.auth
    try:
        return Status(201, start_or_resume_conversation(user.user_id, payload.order_id))
    except UserNotFound as e:
        return Status(404, {"detail": str(e)})


@router.get(
    "/conversations/mine",
    response={200: List[ConversationOut]},
    auth=AllRolesAuth(),
    summary="Conversas do usuário autenticado",
)
@ratelimit(key="user", rate="120/m", block=True)
def list_my_conversations_router(request):
    user: User = request.auth
    return Status(200, list_conversations_for_client(user.user_id))


@router.get(
    "/conversations/admin",
    response={200: List[ConversationOut]},
    auth=AdminOnlyAuth(),
    summary="Inbox do admin (filtro opcional por status)",
)
@ratelimit(key="user", rate="120/m", block=True)
def list_admin_conversations_router(request, status: Optional[str] = None):
    return Status(200, list_conversations_for_admin(status=status))


@router.get(
    "/conversations/{conversation_id}",
    response={200: ConversationOut, 404: DetailOut},
    auth=AllRolesAuth(),
    summary="Detalhe de uma conversa",
)
@ratelimit(key="user", rate="120/m", block=True)
def get_conversation_router(request, conversation_id: uuid.UUID):
    user: User = request.auth
    try:
        return Status(200, get_conversation_for_user(user.user_id, conversation_id))
    except (ConversationNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})


@router.get(
    "/conversations/{conversation_id}/messages",
    response={200: List[MessageOut], 404: DetailOut},
    auth=AllRolesAuth(),
    summary="Histórico de mensagens da conversa",
)
@ratelimit(key="user", rate="120/m", block=True)
def list_messages_router(request, conversation_id: uuid.UUID):
    user: User = request.auth
    try:
        return Status(200, list_messages(user_id=user.user_id, conversation_id=conversation_id))
    except (ConversationNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})


@router.post(
    "/conversations/{conversation_id}/messages",
    response={201: MessageOut, 400: DetailOut, 404: DetailOut},
    auth=AllRolesAuth(),
    summary="Envia mensagem (texto e/ou até 5 anexos) via multipart",
)
@ratelimit(key="user", rate="60/m", block=True)
def send_message_router(
    request,
    conversation_id: uuid.UUID,
    content: Form[str] = "",
    files: File[List[UploadedFile]] = None,
):
    user: User = request.auth
    try:
        message = send_message(
            conversation_id=conversation_id,
            sender_id=user.user_id,
            content=content,
            files=files or [],
        )
        return Status(201, message)
    except (EmptyMessage, TooManyAttachments) as e:
        return Status(400, {"detail": str(e)})
    except (ConversationNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})


@router.post(
    "/conversations/{conversation_id}/read",
    response={200: ReadOut, 404: DetailOut},
    auth=AllRolesAuth(),
    summary="Marca como lidas as mensagens recebidas",
)
@ratelimit(key="user", rate="120/m", block=True)
def mark_read_router(request, conversation_id: uuid.UUID):
    user: User = request.auth
    try:
        updated = mark_conversation_as_read(user_id=user.user_id, conversation_id=conversation_id)
        return Status(200, {"updated": updated})
    except (ConversationNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})