import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from luxury_fashion.apps.core.validators.image_validator import validate_image_file
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.constants.gender import Gender    
from luxury_fashion.apps.core.validators.image_validator import validate_image_file    
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import parse, format_number, PhoneNumberFormat
from datetime import timezone
from django.utils import timezone 
from luxury_fashion.apps.core.validators.validate_cep import validate_cep



class AddressesClient(models.Model):
    class BrazilianState(models.TextChoices):
        AC = "AC", "Acre"
        AL = "AL", "Alagoas"
        AP = "AP", "Amapá"
        AM = "AM", "Amazonas"
        BA = "BA", "Bahia"
        CE = "CE", "Ceará"
        DF = "DF", "Distrito Federal"
        ES = "ES", "Espírito Santo"
        GO = "GO", "Goiás"
        MA = "MA", "Maranhão"
        MT = "MT", "Mato Grosso"
        MS = "MS", "Mato Grosso do Sul"
        MG = "MG", "Minas Gerais"
        PA = "PA", "Pará"
        PB = "PB", "Paraíba"
        PR = "PR", "Paraná"
        PE = "PE", "Pernambuco"
        PI = "PI", "Piauí"
        RJ = "RJ", "Rio de Janeiro"
        RN = "RN", "Rio Grande do Norte"
        RS = "RS", "Rio Grande do Sul"
        RO = "RO", "Rondônia"
        RR = "RR", "Roraima"
        SC = "SC", "Santa Catarina"
        SP = "SP", "São Paulo"
        SE = "SE", "Sergipe"
        TO = "TO", "Tocantins"

    client_id = models.ForeignKey("accounts.Client", on_delete=models.CASCADE, related_name="addresses")
    address_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cep = models.CharField(_("CEP"), max_length=9, validators=[validate_cep])
    street = models.CharField(_("Logradouro"), max_length=255)
    number = models.CharField(_("Número"), max_length=20)
    complement = models.CharField(_("Complemento"), max_length=255, blank=True)
    neighborhood = models.CharField(_("Bairro"), max_length=255)
    city = models.CharField(_("Cidade"), max_length=255)
    state = models.CharField(_("Estado"), max_length=2, choices=BrazilianState)
    country = models.CharField(_("País"), max_length=100, default="Brasil")
    is_preferential = models.BooleanField(_("Preferencial"), default=True)

    def __str__(self):
        return f"{self.street} {self.number}, {self.neighborhood}, {self.city} {self.state} {self.cep}"
    
    class Meta:
        verbose_name = _("Endereço")
        verbose_name_plural = _("Endereços")
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["city"]),
            models.Index(fields=["street", "city"]),
            models.Index(fields=["neighborhood", "city"]),
            models.Index(fields=["cep"]),
        ]
        ordering = ["first_name", "last_name"]


    def save(self, *args, **kwargs):
        if self.is_preferential:
            AddressesClient.objects.filter(client_id=self.client_id, is_preferential=True).exclude(pk=self.pk).update(is_preferential=False)
        super().save(*args, **kwargs)