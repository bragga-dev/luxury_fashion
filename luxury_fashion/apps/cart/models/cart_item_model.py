# checkout_app/models.py
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.core.validators import MinValueValidator


class CartItem(models.Model):
    cart_id = models.ForeignKey("cart.Cart", on_delete=models.CASCADE, related_name="cart_items")
    product_id = models.ForeignKey("products.Product", null=True, blank=True, on_delete=models.CASCADE, related_name="product_items")
    cart_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quantity_item = models.PositiveIntegerField(_("Quantidade "), default=1, validators=[MinValueValidator(1)])
    unit_price_item = models.DecimalField(_("Preço unitário"), max_digits=10, decimal_places=2, default=0)
    shipping_type = models.CharField(_("Tipo de frete"), max_length=255, null=True, blank=True)
    shipping_value = models.DecimalField(_("Preço unitário de frete"), max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = _("Item do carrinho")
        verbose_name_plural = _("Itens do carrinho")

   
    def __str__(self):
        if self.product_id:
            return f"{self.quantity_item} x {self.product_id.product_name}"
        return f"Item {self.cart_item_id}"

    def subtotal(self):
        return (self.unit_price_item * self.quantity_item).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        

    def save(self, *args, **kwargs):
        if not self.unit_price_item:
            if self.product_id:
                self.unit_price_item = self.product_id.variants.price
        self.full_clean()
        super().save(*args, **kwargs)

