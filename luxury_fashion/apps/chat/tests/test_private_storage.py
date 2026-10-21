# backend/luxury_fashion/apps/chat/tests/test_private_storage.py
"""URL dos anexos do chat: assinada, do bucket privado e alcançável pelo navegador."""
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import override_settings

from luxury_fashion.config.storages import PrivateFilesStorage

DEV_SETTINGS = dict(
    AWS_S3_CUSTOM_DOMAIN="localhost:9000/luxuryfashionmedia",  # config real de dev: aponta pro bucket de MÍDIA
    AWS_QUERYSTRING_AUTH=False,
    AWS_S3_ENDPOINT_URL="http://minio:9000",  # endpoint interno do Docker
    AWS_ACCESS_KEY_ID="app-user",
    AWS_SECRET_ACCESS_KEY="app-secret",
    AWS_S3_REGION_NAME="us-east-1",
)


@pytest.fixture
def external(monkeypatch):
    monkeypatch.setenv("MINIO_EXTERNAL_URL", "http://localhost:9000")


def test_url_usa_bucket_privado_host_publico_e_assinatura(external):
    with override_settings(**DEV_SETTINGS):
        url = PrivateFilesStorage().url("chat/2026/foto.png")
    parsed = urlparse(url)
    assert parsed.scheme == "http" and parsed.netloc == "localhost:9000"  # não é minio:9000 nem https
    assert parsed.path == "/luxuryfashionprivate/chat/2026/foto.png"       # não é o bucket de mídia
    query = parse_qs(parsed.query)
    assert "X-Amz-Signature" in query and query["X-Amz-Expires"] == ["3600"]


def test_sem_endpoint_publico_usa_o_comportamento_padrao(monkeypatch):
    monkeypatch.delenv("MINIO_EXTERNAL_URL", raising=False)
    with override_settings(**DEV_SETTINGS):
        url = PrivateFilesStorage().url("chat/a.png")
    assert "luxuryfashionmedia" not in url  # nunca o bucket público de mídia
    assert "Signature=" in url or "X-Amz-Signature" in url  # sempre assinada (V2 ou V4)