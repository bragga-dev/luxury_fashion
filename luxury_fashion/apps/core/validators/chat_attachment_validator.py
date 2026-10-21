import os

import magic
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import FieldFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

# =========================================================
# VALIDAÇÃO DE ANEXO DE CHAT (foto, vídeo, PDF, TXT)
# =========================================================
# Duas camadas: extensão decide qual conjunto de regras aplicar, e
# `python-magic` (libmagic) confere o CONTEÚDO real dos primeiros bytes
# do arquivo — pega o caso de alguém renomear um .exe pra .pdf pra passar
# pela validação de extensão. Imagem, além disso, é reaberta com Pillow
# pra confirmar que decodifica de verdade (mesmo rigor já usado nas
# imagens de produto).

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt"}

ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS

MAX_IMAGE_SIZE_MB = 5
MAX_VIDEO_SIZE_MB = 50
MAX_DOCUMENT_SIZE_MB = 10

VALID_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF"}

EXPECTED_MIME_BY_EXTENSION = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".avif": {"image/avif", "image/avif-sequence"},
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime", "video/mp4"},
    ".webm": {"video/webm"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
}
_SNIFF_BYTES = 2048


class ChatAttachmentType:
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


def get_attachment_type(filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    if ext in IMAGE_EXTENSIONS:
        return ChatAttachmentType.IMAGE
    if ext in VIDEO_EXTENSIONS:
        return ChatAttachmentType.VIDEO
    if ext in DOCUMENT_EXTENSIONS:
        return ChatAttachmentType.DOCUMENT
    raise ValidationError(
        _("Extensão '%(ext)s' não suportada. Use: %(valid)s."),
        params={"ext": ext, "valid": ", ".join(sorted(ALL_EXTENSIONS))},
    )


def _sniff_mime(value) -> str:
    value.seek(0)
    header = value.read(_SNIFF_BYTES)
    value.seek(0)
    return magic.from_buffer(header, mime=True)


def _validate_content_matches_extension(value, ext: str) -> None:
    detected_mime = _sniff_mime(value)
    expected = EXPECTED_MIME_BY_EXTENSION.get(ext, set())
    if detected_mime not in expected:
        raise ValidationError(
            _(
                "O conteúdo do arquivo (%(detected)s) não corresponde à extensão "
                "'%(ext)s'. Isso costuma acontecer quando um arquivo é renomeado "
                "pra outra extensão."
            ),
            params={"detected": detected_mime, "ext": ext},
        )


def validate_chat_attachment_file(value) -> None:
    # Via model/full_clean o validator recebe um FieldFile, não o UploadedFile.
    # Se ainda não foi salvo no storage, o upload original está em `.file`.
    if isinstance(value, FieldFile):
        if value._committed:
            return  # já está no storage: não revalida
        value = value.file
    if not isinstance(value, UploadedFile):
        return

    ext = os.path.splitext(value.name)[-1].lower()
    attachment_type = get_attachment_type(value.name)

    _validate_content_matches_extension(value, ext)

    if attachment_type == ChatAttachmentType.IMAGE:
        _validate_image(value)
    elif attachment_type == ChatAttachmentType.VIDEO:
        _validate_size(value, MAX_VIDEO_SIZE_MB)
    else:
        _validate_size(value, MAX_DOCUMENT_SIZE_MB)


def _validate_size(value, max_mb: int) -> None:
    if value.size > max_mb * 1024 * 1024:
        raise ValidationError(
            _("O arquivo (%(size).1f MB) excede o limite de %(max)s MB."),
            params={"size": value.size / (1024 * 1024), "max": max_mb},
        )


def _validate_image(value) -> None:
    _validate_size(value, MAX_IMAGE_SIZE_MB)
    try:
        value.seek(0)
        img = Image.open(value)
        img.verify()
        value.seek(0)
        img = Image.open(value)
        if (img.format or "").upper() not in VALID_IMAGE_FORMATS:
            raise ValidationError(
                _("Formato de imagem '%(fmt)s' não suportado."), params={"fmt": img.format}
            )
    except UnidentifiedImageError:
        raise ValidationError(_("O arquivo não é uma imagem reconhecida."))
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(_("Arquivo de imagem inválido ou corrompido."))
    finally:
        value.seek(0)