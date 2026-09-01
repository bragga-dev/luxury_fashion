import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    cart_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")
    total_price = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    total_shipping = models.DecimalField(_("Preço total de frete"), max_digits=10, decimal_places=2, default=0)
    total_geral = models.DecimalField(_("Total geral"), max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Carrinho")
        verbose_name_plural = _("Carrinhos")

    def __str__(self):
        return f"Carrinho {self.cart_id} - {self.user_id}"

    def calculate_total_price(self) -> Decimal:
        return sum((item.subtotal() for item in self.items.all()), Decimal("0.00"))

    def calculate_total_shipping(self) -> Decimal:
        return sum((item.shipping_value or Decimal("0.00") for item in self.items.all()), Decimal("0.00"))

    def update_totals(self):
        self.total_price = self.calculate_total_price()
        self.total_shipping = self.calculate_total_shipping()
        self.total_geral = self.total_price + self.total_shipping
        self.save(update_fields=["total_price", "total_shipping", "total_geral"])