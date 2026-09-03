import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from luxury_fashion.apps.core.validators.image_validator import validate_image_file


def product_image_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"products/{instance.product_id_id}/{uuid.uuid4().hex}.{extension}"


class ProductImage(models.Model):
    image_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="images")
    product_image = models.ImageField(_("Imagem"), upload_to=product_image_path, validators=[validate_image_file])
    is_cover = models.BooleanField(_("Imagem principal"), default=False)
    display_order = models.PositiveIntegerField(_("Ordem"), default=0)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Imagem do produto")
        verbose_name_plural = _("Imagens dos produtos")
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_id"],
                condition=models.Q(is_cover=True),
                name="unique_cover_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Imagem de {self.product_id.product_name}"