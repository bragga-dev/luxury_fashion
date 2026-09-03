import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class CartItem(models.Model):
    cart_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart_id = models.ForeignKey("cart.Cart", on_delete=models.CASCADE, related_name="items")
    variant_id = models.ForeignKey("products.ProductVariant", on_delete=models.CASCADE, related_name="cart_items")
    quantity_item = models.PositiveIntegerField(_("Quantidade"), default=1, validators=[MinValueValidator(1)])
    unit_price_item = models.DecimalField(_("Preço unitário"), max_digits=10, decimal_places=2, default=0)
    shipping_type = models.CharField(_("Tipo de frete"), max_length=255, null=True, blank=True)
    shipping_value = models.DecimalField(_("Preço unitário de frete"), max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Item do carrinho")
        verbose_name_plural = _("Itens do carrinho")
        constraints = [
            models.UniqueConstraint(fields=["cart_id", "variant_id"], name="unique_variant_per_cart"),
        ]

    def __str__(self):
        return f"{self.quantity_item} x {self.variant_id}"

    def subtotal(self) -> Decimal:
        return (self.unit_price_item * self.quantity_item).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        if not self.unit_price_item:
            self.unit_price_item = self.variant_id.price
        self.full_clean()
        super().save(*args, **kwargs)