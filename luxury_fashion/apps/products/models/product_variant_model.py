from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
from django.core.validators import MinValueValidator
from luxury_fashion.apps.products.models.product_model import Product


class ProductVariant(models.Model):
    variant_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="variants")
    size  =  models.CharField(_("Tamanho"), max_length=5, choices=Product.ProductSize.choices, blank=True, null=True)
    color = models.CharField(_("Cor"), max_length=20, choices=Product.ProductColor.choices, blank=True, null=True)
    gender = models.CharField(_("Gênero"), max_length=20, choices=Product.ProductGender.choices, blank=True, null=True)
    price = models.DecimalField(_("Preço"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0, message=_("O preço não pode ser negativo"))])
    stock = models.PositiveIntegerField(_("Estoque"), validators=[MinValueValidator(0, message=_("O estoque não pode ser negativo"))], default=0)
    description = models.TextField(_("Descrição"), blank=True, default="")
    is_active = models.BooleanField(_("Ativa?"), default=True)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizada em"), auto_now=True)

    class Meta:
        verbose_name = _("Variante de produto")
        verbose_name_plural = _("Variantes de produto")
        ordering = ["product_id", "size", "color", "gender"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_id", "size", "color", "gender"],
                name="unique_variant_per_product_size_color_gender",
            ),
        ]

    def __str__(self):
        return f"{self.product_id.product_name} — {self.size}/{self.color}"

    @property
    def in_stock(self) -> bool:
        return self.is_active and self.stock > 0