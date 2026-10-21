import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    cart_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")
    # Frete NÃO mora no carrinho: o cliente só cota (POST /cart/shipping/quote) e o frete escolhido
    # é recotado e gravado no pedido. Por isso o carrinho só tem o subtotal.
    total_price = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Carrinho")
        verbose_name_plural = _("Carrinhos")

    def __str__(self):
        return f"Carrinho {self.cart_id} - {self.user_id}"

    def calculate_total_price(self) -> Decimal:
        from luxury_fashion.apps.cart.models.cart_item_model import CartItem

        items = CartItem.objects.filter(cart_id=self)
        return sum((item.subtotal() for item in items), Decimal("0.00"))

    def update_totals(self):
        self.total_price = self.calculate_total_price()
        self.save(update_fields=["total_price"])