import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrderItem(models.Model):
    order_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.ForeignKey("payments.Order", on_delete=models.CASCADE, related_name="items")
    variant_id = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="order_items")
    order_item_quantity = models.PositiveIntegerField(_("Quantidade"), default=1, validators=[MinValueValidator(1)])
    order_item_price = models.DecimalField(_("Preço unitário"), max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = _("Item do pedido")
        verbose_name_plural = _("Itens do pedido")

    def subtotal(self) -> Decimal:
        return (self.order_item_price * self.order_item_quantity).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def __str__(self):
        return f"{self.order_item_quantity} x {self.variant_id}"