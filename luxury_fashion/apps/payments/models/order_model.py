from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
from django.core.validators import MinValueValidator
from luxury_fashion.apps.core.utils.generate_random_code import generate_random_code





class Order(models.Model):
    class OrderPaymentMethods(models.TextChoices):
        PIX = "pix", _("PIX")
        CARTAO = "cartão", _("Cartão")
        BOLETO = "boleto", _("Boleto")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendente")
        PROCESSING = "processing", _("Processando")
        COMPLETED = "completed", _("Completo")
        CANCELLED = "cancelled", _("Cancelado")
        REFUNDED = "refunded", _("Reembolsado")
        FAILED = "failed", _("Falhou")

    user_id = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="orders")
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_("Código"), max_length=12, default=generate_random_code, editable=False, unique=True)
    status = models.CharField(_("Status"), max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(_("Método de Pagamento"), max_length=10, choices=OrderPaymentMethods.choices, default=OrderPaymentMethods.PIX)
    total_geral = models.DecimalField(_("Preço total"), max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    order_shipping_total = models.DecimalField(_("Preço total de frete"), max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Data da compra"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Data de atualização"), auto_now_add=True)

    class Meta:
        verbose_name = _("Pedido")
        verbose_name_plural = _("Pedidos")
    
    def __str__(self):
        return f"Pedido {self.code} - {self.user_id.email}"

