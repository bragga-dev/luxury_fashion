import uuid

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        ORDER_PAID = "ORDER_PAID", _("Pagamento confirmado")
        ORDER_CANCELLED = "ORDER_CANCELLED", _("Pedido cancelado")
        ORDER_EXPIRED = "ORDER_EXPIRED", _("Pedido expirado")
        ORDER_REFUNDED = "ORDER_REFUNDED", _("Pedido reembolsado")
        ORDER_SHIPPED = "ORDER_SHIPPED", _("Pedido enviado")
        ORDER_IN_TRANSIT = "ORDER_IN_TRANSIT", _("Pedido em transporte")
        ORDER_DELIVERED = "ORDER_DELIVERED", _("Pedido entregue")
        REVIEW_PUBLISHED = "REVIEW_PUBLISHED", _("Avaliação publicada")
        REVIEW_REQUEST = "REVIEW_REQUEST", _("Convite para avaliar a compra")
        PROMOTION = "PROMOTION", _("Promoção")
        NEW_ORDER_PAID = "NEW_ORDER_PAID", _("Novo pedido pago")
        REVIEW_PENDING = "REVIEW_PENDING", _("Avaliação aguardando moderação")
        PROFILE_INCOMPLETE = "profile_incomplete", _("Perfil incompleto")
        SYSTEM = "SYSTEM", _("Aviso do sistema")

    class TargetType(models.TextChoices):
        ORDER = "order", _("Pedido")
        REVIEW = "review", _("Avaliação")

    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Destinatário"),
    )
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        verbose_name=_("Autor do evento"),
        help_text=_("Quem originou o evento (ex.: admin que aprovou), se houver."),
    )

    type = models.CharField(_("Tipo"), max_length=30, choices=NotificationType.choices)
    title = models.CharField(_("Título"), max_length=120)
    body = models.CharField(_("Mensagem"), max_length=255, blank=True, default="")
    action_url = models.CharField(_("URL de ação (relativa)"), max_length=300, blank=True, default="")

    target_type = models.CharField(_("Tipo do alvo"), max_length=30, choices=TargetType.choices, blank=True, default="")
    target_id = models.UUIDField(_("ID do alvo"), null=True, blank=True)

    dedupe_key = models.CharField(_("Chave de idempotência"), max_length=120, null=True, blank=True)
    read_at = models.DateTimeField(_("Lida em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notificação")
        verbose_name_plural = _("Notificações")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"], name="notif_rcpt_created_idx"),
            models.Index(fields=["recipient"], condition=Q(read_at__isnull=True), name="notif_rcpt_unread_idx"),
            models.Index(
                fields=["target_type", "target_id"],
                condition=Q(target_id__isnull=False),
                name="notif_target_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=Q(dedupe_key__isnull=False),
                name="uniq_notif_rcpt_dedupe",
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} → {self.recipient_id} ({'lida' if self.read_at else 'nova'})"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None