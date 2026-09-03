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

from luxury_fashion.apps.core.validators.validate_cpf_or_cnpj import validate_cpf

def client_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/{instance.id}/{uuid.uuid4().hex}.{ext}"

DEFAULT_CLIENT_PHOTO = "default/client_img.jpg"




class Client(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    client_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(_("Nome"), max_length=255, blank=True, null=True)
    last_name = models.CharField(_("Sobrenome"), max_length=255, blank=True, null=True)
    username = models.CharField(_("Nome de usuário"), max_length=150, unique=True, blank=True, null=True)
    phone = PhoneNumberField(region="BR", blank=True, default="", null=True, help_text=_('Número de telefone no formato internacional, ex: +55 11 99999-8888.'),)
    gender = models.CharField(_("Gênero"), max_length=10, choices=Gender.CHOICES, default=Gender.OTHER)
    birth_date = models.DateField(_("Data de nascimento"), blank=True, null=True)
    photo = models.ImageField(upload_to=client_photo_path, default=DEFAULT_CLIENT_PHOTO, blank=True, null=True, validators=[validate_image_file], help_text=_('Formatos aceitos: jpg, jpeg ou png. Máx: 5MB.'))
    asaas_customer_id = models.CharField(_("ID do cliente na Asaas"), max_length=50, blank=True, null=True, db_index=True)
    cpf = models.CharField(_("CPF"), max_length=11, blank=True, null=True, validators=[validate_cpf])

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_id.email})"
    
    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        indexes = [
            models.Index(fields=["first_name", "last_name"]),
        ]
        ordering = ["first_name", "last_name"]


    @property
    def photo_url(self) -> str:
        if self.photo and self.photo.name != DEFAULT_CLIENT_PHOTO:
            try:
                return self.photo.url
            except Exception:
                pass
        return self.photo.storage.url(DEFAULT_CLIENT_PHOTO)    
    

    def get_full_name(self):
        full_name = " ".join(filter(None, [self.first_name, self.last_name])).strip()
        return full_name or self.username or f"Client {self.client_id}"
    
    @staticmethod
    def normalize_phone(phone_str: str) -> str:
        number = parse(phone_str, "BR")
        return format_number(number, PhoneNumberFormat.E164)

    def clean(self):
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError(
                {'birth_date': _('Data de nascimento não pode ser no futuro.')}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.photo:
            self.photo = DEFAULT_CLIENT_PHOTO
        super().save(*args, **kwargs)