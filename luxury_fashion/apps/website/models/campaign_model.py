import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Campaign(models.Model):
    campaign_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_("Título"), max_length=100, unique=True, blank=False, null=False)
    description = models.TextField(_("Descrição"), max_length=500, null=True, blank=True)
    is_active = models.BooleanField(_("Ativo?"), default=False)
    starts_at = models.DateTimeField(_("Início da campanha"), null=True, blank=True)
    ends_at = models.DateTimeField(_("Fim da campanha"), null=True, blank=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Campanha")
        verbose_name_plural = _("Campanhas")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.title