import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from luxury_fashion.apps.core.utils.generate_random_code import generate_random_code


class Order(models.Model):
    class StatusOrder(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        PROCESSING = "PROCESSING", _("Processando")
        COMPLETED = "COMPLETED", _("Completo")
        CANCELLED = "CANCELLED", _("Cancelado")
        REFUNDED = "REFUNDED", _("Reembolsado")
        FAILED = "FAILED", _("Falhou")

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    shipping_address = models.ForeignKey(
        "accounts.AddressesClient",
        on_delete=models.PROTECT,
        related_name="orders",
        help_text=_("Snapshot do endereço no momento da compra."),
    )
    code = models.CharField(_("Código"), max_length=12, default=generate_random_code, editable=False, unique=True)
    order_status = models.CharField(_("Status"), max_length=15, choices=StatusOrder.choices, default=StatusOrder.PENDING)
    total_geral = models.DecimalField(_("Preço total"), max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    order_shipping_total = models.DecimalField(_("Preço total de frete"), max_digits=10, decimal_places=2, default=0)
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