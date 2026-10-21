"""
Fixtures compartilhadas dos testes do chat.

Banco: sqlite em memória. Channel layer: em memória (ver settings/test.py).
Storage de anexos: o FileField do MessageAttachment fixa PrivateFilesStorage (MinIO)
direto no campo, então `chat_storage` troca por um FileSystemStorage em tmp_path.
"""
import io

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja_jwt.tokens import RefreshToken
from PIL import Image

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.chat.models.conversation_model import Conversation
from luxury_fashion.apps.chat.models.message_attachment_model import MessageAttachment


@pytest.fixture
def client_user(db) -> User:
    return User.objects.create_user(
        email="cliente@example.com", password="senha-super-segura-123", is_active=True, is_trusty=True
    )


@pytest.fixture
def other_client(db) -> User:
    return User.objects.create_user(
        email="outro@example.com", password="senha-super-segura-123", is_active=True, is_trusty=True
    )


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_superuser(email="admin@example.com", password="senha-super-segura-123")


@pytest.fixture
def conversation(client_user) -> Conversation:
    return Conversation.objects.create(client=client_user)


@pytest.fixture
def chat_storage(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=str(tmp_path), base_url="/private/")
    monkeypatch.setattr(MessageAttachment._meta.get_field("file"), "storage", storage)
    return storage


@pytest.fixture
def png_file() -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
    return SimpleUploadedFile("foto.png", buf.getvalue(), content_type="image/png")


@pytest.fixture
def txt_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("nota.txt", b"ola, tudo bem?\n", content_type="text/plain")


@pytest.fixture
def fake_pdf_exe() -> SimpleUploadedFile:
    """Executável (cabeçalho MZ) renomeado pra .pdf — deve ser barrado pelo libmagic."""
    return SimpleUploadedFile("fatura.pdf", b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64, content_type="application/pdf")


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def access_token(user) -> str:
    return str(RefreshToken.for_user(user).access_token)