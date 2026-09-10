from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
from luxury_fashion.apps.core.validators.image_validator import validate_image_file



def product_campaign_image_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"Campaign/{instance.campaign_mage_id_id}/{uuid.uuid4().hex}.{extension}"







class CampaignImage(models.Model):
    campaign_mage_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign_id = models.ForeignKey("website.Campaign", related_name="campaign")
    image = models.ImageField(_("Banner"), upload_to=product_campaign_image_path, validators=[validate_image_file])
    dispaly_order = models.PositiveIntegerField(_("Ordem"), default=0)
    
 
    class Meta:
        verbose_name = _("Imagem da Campanha")
        verbose_name_plural = _("Imagens das Campanhas")
        ordering = ["display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign_id"],
                condition=models.Q(is_cover=True),
                name="unique_cover_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Imagem de {self.campaign_id.title}"