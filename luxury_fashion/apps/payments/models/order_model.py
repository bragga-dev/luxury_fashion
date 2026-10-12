import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from luxury_fashion.apps.core.exceptions.payment_exception import InvalidOrderStatusTransition
from luxury_fashion.apps.core.utils.generate_random_code import generate_random_code


class Order(models.Model):
    class StatusOrder(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        COMPLETED = "COMPLETED", _("Completo")
        CANCELLED = "CANCELLED", _("Cancelado")
        REFUNDED = "REFUNDED", _("Reembolsado")
        FAILED = "FAILED", _("Falhou")

    class ShippingStatus(models.TextChoices):
        PENDING = "pending", "Aguardando envio"
        LABEL_GENERATED = "label_generated", "Etiqueta gerada"
        SHIPPED = "shipped", "Enviado"
        IN_TRANSIT = "in_transit", "Em transporte"
        DELIVERED = "delivered", "Entregue"

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

    shipping_service_code = models.CharField(_("Código do serviço Frenet"), max_length=50, blank=True, null=True, help_text=_("Service code retornado pela cotação Frenet e escolhido pelo cliente no checkout."))
    shipping_service_name = models.CharField(_("Serviço de frete"), max_length=255, blank=True, null=True)
    shipping_delivery_days = models.PositiveIntegerField(_("Prazo de entrega prometido (dias)"), blank=True, null=True)
    frenet_order_id = models.CharField(max_length=100, blank=True, null=True)
    shipping_tracking_code = models.CharField(max_length=100, blank=True, null=True)
    shipping_label_url = models.URLField(blank=True, null=True)
    shipping_status = models.CharField(max_length=30, choices=ShippingStatus.choices, default=ShippingStatus.PENDING)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(_("Entregue em"), blank=True, null=True)

    class Meta:
        verbose_name = _("Pedido")
        verbose_name_plural = _("Pedidos")
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["order_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["shipping_status"]),
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

    def mark_delivered(self) -> None:
        """Marca a entrega. As pré-condições de negócio ficam no service (order_delivery_service)."""
        self.shipping_status = self.ShippingStatus.DELIVERED
        self.delivered_at = self.delivered_at or timezone.now()
        self.save(update_fields=["shipping_status", "delivered_at", "updated_at"])