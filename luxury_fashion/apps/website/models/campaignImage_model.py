import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from luxury_fashion.apps.core.validators.image_validator import validate_image_file


def campaign_image_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"campaigns/{instance.campaign_id_id}/{uuid.uuid4().hex}.{extension}"


class CampaignImage(models.Model):
    campaign_mage_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign_id = models.ForeignKey("website.Campaign", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(_("Banner"), upload_to=campaign_image_path, validators=[validate_image_file])
    is_cover = models.BooleanField(_("Imagem principal"), default=False)
    display_order = models.PositiveIntegerField(_("Ordem"), default=0)
    fit = models.CharField(max_length=7, choices=[("cover", "Preencher"), ("contain", "Mostrar inteira")], default="cover")
    focus_x = models.PositiveSmallIntegerField(default=50, validators=[MaxValueValidator(100)])
    focus_y = models.PositiveSmallIntegerField(default=50, validators=[MaxValueValidator(100)])
    zoom = models.FloatField(default=1.0, validators=[MinValueValidator(1.0), MaxValueValidator(3.0)])
    title = models.CharField(max_length=120, blank=True, default="")
    subtitle = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Imagem da Campanha")
        verbose_name_plural = _("Imagens das Campanhas")
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign_id"],
                condition=models.Q(is_cover=True),
                name="unique_cover_image_per_campaign",
            ),
        ]

    def __str__(self):
        return f"Imagem de {self.campaign_id.title}"