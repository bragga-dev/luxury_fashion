from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
import uuid

class ProductShipping(models.Model):
    product_shipping_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant_id = models.OneToOneField("products.ProductVariant", on_delete=models.CASCADE, related_name="shipping")
    weight = models.DecimalField(_("Peso (kg)"), max_digits=6, decimal_places=3, validators=[MinValueValidator(0.001, message=_("O peso deve ser maior que zero"))])
    height = models.DecimalField(_("Altura (cm)"), max_digits=6, decimal_places=2, validators=[MinValueValidator(0.1, message=_("A altura deve ser maior que zero"))])
    width = models.DecimalField(_("Largura (cm)"), max_digits=6, decimal_places=2, validators=[MinValueValidator(0.1, message=_("A largura deve ser maior que zero"))])
    length = models.DecimalField(_("Comprimento (cm)"), max_digits=6, decimal_places=2, validators=[MinValueValidator(0.1, message=_("O comprimento deve ser maior que zero"))])
    quantity = models.PositiveIntegerField(_("Quantidade por embalagem"), default=1, validators=[MinValueValidator(1, message=_("A quantidade deve ser pelo menos 1"))], help_text=_("Quantidade padrão de itens desta variante por embalagem, usada como base para a cotação de frete."))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Dados de frete do produto")
        verbose_name_plural = _("Dados de frete dos produtos")

    def __str__(self):
        return f"Frete de {self.variant_id}"

    def to_shipping_payload(self) -> dict:
        """Monta o dicionário no formato esperado por APIs de frete (ex: Melhor Envio)."""
        return {"weight": float(self.weight), "height": float(self.height), "width": float(self.width), "length": float(self.length), "quantity": self.quantity}
