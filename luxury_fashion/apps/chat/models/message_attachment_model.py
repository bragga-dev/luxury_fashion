# luxury_fashion/apps/chat/models/message_attachment_model.py
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from luxury_fashion.apps.core.validators.chat_attachment_validator import (
    ChatAttachmentType,
    validate_chat_attachment_file,
)
from luxury_fashion.config.storages import PrivateFilesStorage


def chat_attachment_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    conversation_id = instance.message.conversation_id
    return f"chat/{conversation_id}/{instance.message_id}/{uuid.uuid4().hex}.{extension}"


class MessageAttachment(models.Model):
    """
    Um arquivo anexado a uma mensagem (foto, vídeo, PDF ou TXT). Uma
    mensagem pode ter vários — ex: cliente manda 2 fotos do defeito numa
    tacada só.

    Fica no bucket PRIVADO (URL assinada, expira) — diferente das imagens
    de produto, que são públicas na vitrine.
    """

    class FileType(models.TextChoices):
        IMAGE = ChatAttachmentType.IMAGE, _("Imagem")
        VIDEO = ChatAttachmentType.VIDEO, _("Vídeo")
        DOCUMENT = ChatAttachmentType.DOCUMENT, _("Documento")

    attachment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey("chat.Message", on_delete=models.CASCADE, related_name="attachments", verbose_name=_("Mensagem"))
    file = models.FileField(_("Arquivo"), upload_to=chat_attachment_path, storage=PrivateFilesStorage(), validators=[validate_chat_attachment_file])
    file_type = models.CharField(_("Tipo"), max_length=10, choices=FileType.choices)
    original_filename = models.CharField(_("Nome original"), max_length=255)
    file_size = models.PositiveIntegerField(_("Tamanho (bytes)"))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Anexo")
        verbose_name_plural = _("Anexos")
        ordering = ["created_at"]

    def __str__(self):
        return self.original_filename