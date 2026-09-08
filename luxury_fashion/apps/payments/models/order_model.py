import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from luxury_fashion.apps.core.exceptions.service_exception import  InvalidOrderStatusTransition
from luxury_fashion.apps.core.utils.generate_random_code import generate_random_code


class Order(models.Model):
    class StatusOrder(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        COMPLETED = "COMPLETED", _("Completo")
        CANCELLED = "CANCELLED", _("Cancelado")
        REFUNDED = "REFUNDED", _("Reembolsado")
        FAILED = "FAILED", _("Falhou")

    # PENDING = aguardando pagamento (é criado assim e permanece até o
    # webhook da Asaas confirmar ou algo dar errado). Não existe estado
    # intermediário "PROCESSING" — o Payment em si já tem status próprio
    # pra acompanhar a cobrança em andamento; duplicar isso no Order só
    # criaria dois lugares pra sincronizar.
    ALLOWED_TRANSITIONS = {
        StatusOrder.PENDING: {StatusOrder.COMPLETED, StatusOrder.CANCELLED, StatusOrder.FAILED},
        StatusOrder.COMPLETED: {StatusOrder.REFUNDED},
        StatusOrder.CANCELLED: set(),
        StatusOrder.REFUNDED: set(),
        StatusOrder.FAILED: set(),
    }

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    shipping_address = models.ForeignKey("accounts.AddressesClient", on_delete=models.PROTECT, related_name="orders", help_text=_("Snapshot do endereço no momento da compra."),)
    code = models.CharField(_("Código"), max_length=12, default=generate_random_code, editable=False, unique=True)
    order_status = models.CharField(_("Status"), max_length=15, choices=StatusOrder.choices, default=StatusOrder.PENDING)
    total_geral = models.DecimalField(_("Preço total"), max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    order_shipping_total = models.DecimalField(_("Preço total de frete"), max_digits=10, decimal_places=2, default=0)
    canceled_at = models.DateTimeField(_("Cancelado em"), null=True, blank=True)
    canceled_reason = models.CharField(_("Motivo do cancelamento"), max_length=255, null=True, blank=True)
    completed_at = models.DateTimeField(_("Concluído em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Data da compra"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Data de atualização"), auto_now=True)

    class Meta:
        verbose_name = _("Pedido")
        verbose_name_plural = _("Pedidos")
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["order_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"Pedido {self.code} - {self.user_id.email}"

    def can_transition_to(self, target_status: str) -> bool:
        return target_status in self.ALLOWED_TRANSITIONS.get(self.order_status, set())

    def _ensure_transition_allowed(self, target_status: str) -> None:
        if not self.can_transition_to(target_status):
            raise InvalidOrderStatusTransition(
                _("Não é possível mudar de %(current)s para %(target)s.") % {
                    "current": self.get_order_status_display(),
                    "target": dict(self.StatusOrder.choices).get(target_status, target_status),
                }
            )

    def cancel(self, reason: str) -> None:
        self._ensure_transition_allowed(self.StatusOrder.CANCELLED)
        self.order_status = self.StatusOrder.CANCELLED
        self.canceled_at = timezone.now()
        self.canceled_reason = reason
        self.save(update_fields=["order_status", "canceled_at", "canceled_reason", "updated_at"])

    def fail(self) -> None:
        self._ensure_transition_allowed(self.StatusOrder.FAILED)
        self.order_status = self.StatusOrder.FAILED
        self.save(update_fields=["order_status", "updated_at"])

    def complete(self) -> None:
        self._ensure_transition_allowed(self.StatusOrder.COMPLETED)
        self.order_status = self.StatusOrder.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["order_status", "completed_at", "updated_at"])

    def refund(self) -> None:
        self._ensure_transition_allowed(self.StatusOrder.REFUNDED)
        self.order_status = self.StatusOrder.REFUNDED
        self.save(update_fields=["order_status", "updated_at"])