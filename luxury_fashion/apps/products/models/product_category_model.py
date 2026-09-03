from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 

from luxury_fashion.apps.core.validators.image_validator import validate_image_file

def category_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"category_image/{instance.product_category_id}/{uuid.uuid4().hex}.{ext}"

DEFAULT_CATEGORY_IMAGE = "default/category_img.jpg"



class ProductCategory(models.Model):
    
    product_category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(_("Nome"), max_length=100, blank=False, null=False)
    category_image = models.ImageField(upload_to=category_image_path, default=DEFAULT_CATEGORY_IMAGE, blank=True, null=True, validators=[validate_image_file], help_text=_('Formatos aceitos: jpg, jpeg ou png. Máx: 5MB.'))
    is_active = models.BooleanField(_("Ativa?"), default=True)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizada em"), auto_now=True)

    class Meta:
        verbose_name = _("Categoria de Produto")
        verbose_name_plural = _("Categorias de Produtos")
        ordering = ["category_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category_name"],
                name="unique_category_name",
            ),
        ]

    def __str__(self):
        return f"{self.category_name}"

    @property
    def category_image_url(self) -> str:
        if self.category_image and self.category_image.name != DEFAULT_CATEGORY_IMAGE:
            try:
                return self.category_image.url
            except Exception:
                pass
        return self.category_image.storage.url(DEFAULT_CATEGORY_IMAGE)    
    
  