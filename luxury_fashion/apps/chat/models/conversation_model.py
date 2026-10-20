# luxury_fashion/apps/chat/models/conversation_model.py
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    """
    Uma "sala" de atendimento entre um cliente e a loja. Não é 1 admin ↔ 1
    cliente — qualquer admin pode ver e responder (`assigned_admin` é só
    indicativo de quem está cuidando, não trava a conversa pra ele).
    """

    class Status(models.TextChoices):
        OPEN = "open", _("Aberta")
        CLOSED = "closed", _("Encerrada")

    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="conversations", verbose_name=_("Cliente"))
    assigned_admin = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
        null=True,
        blank=True,
        verbose_name=_("Admin responsável"),
        help_text=_("Quem está cuidando desta conversa no momento. Opcional — qualquer admin pode responder."),
    )
    order = models.ForeignKey(
        "payments.Order",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
        verbose_name=_("Pedido relacionado"),
        help_text=_("Preenchido quando a conversa é sobre um pedido específico."),
    )

    subject = models.CharField(_("Assunto"), max_length=140, blank=True)
    status = models.CharField(_("Status"), max_length=10, choices=Status.choices, default=Status.OPEN)

    last_message_at = models.DateTimeField(_("Última mensagem em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizada em"), auto_now=True)

    class Meta:
        verbose_name = _("Conversa")
        verbose_name_plural = _("Conversas")
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["client", "-last_message_at"]),
            models.Index(fields=["status", "-last_message_at"]),
        ]

    def __str__(self):
        return f"Conversa {self.conversation_id} — {self.client}"

    def open_conversation(self):
        if self.status == self.Status.CLOSED:
            self.status = self.Status.OPEN
            self.save(update_fields=["status"])

    
    def close_conversation(self):
        if self.status == self.Status.OPEN:
            self.status = self.Status.CLOSED
            self.save(update_fields=["status"])