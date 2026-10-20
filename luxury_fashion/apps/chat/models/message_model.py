import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey("chat.Conversation", on_delete=models.CASCADE, related_name="messages", verbose_name=_("Conversa"))
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="sent_messages", verbose_name=_("Remetente"))
    content = models.TextField(_("Mensagem"), blank=True)
    is_read = models.BooleanField(_("Lida"), default=False)
    read_at = models.DateTimeField(_("Lida em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Enviada em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Mensagem")
        verbose_name_plural = _("Mensagens")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
        ]

    def __str__(self):
        preview = self.content[:30] if self.content else "[anexo]"
        return f"{self.sender}: {preview}"

    def clean(self):
        super().clean()

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])