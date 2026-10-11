import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from luxury_fashion.apps.core.validators.image_validator import validate_image_file
from luxury_fashion.apps.accounts.models.user_model import User


def admin_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"photos/admin/{instance.admin_id}/{uuid.uuid4().hex}.{ext}"


DEFAULT_ADMIN_PHOTO = "default/admin_img.jpg"


class AdminProfile(models.Model):
    user_id = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    admin_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(_("Nome completo"), max_length=255)
    photo = models.ImageField(
        upload_to=admin_photo_path,
        default=DEFAULT_ADMIN_PHOTO,
        blank=True,
        null=True,
        validators=[validate_image_file],
        help_text=_('Formatos aceitos: jpg, jpeg ou png. Máx: 5MB.'),
    )

    class Meta:
        verbose_name = _("Perfil do Administrador")
        verbose_name_plural = _("Perfis dos Administradores")
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.user_id.email})"

    @property
    def photo_url(self) -> str:
        if self.photo and self.photo.name != DEFAULT_ADMIN_PHOTO:
            try:
                return self.photo.url
            except Exception:
                pass
        return self.photo.storage.url(DEFAULT_ADMIN_PHOTO)

    def save(self, *args, **kwargs):
        if not self.photo:
            self.photo = DEFAULT_ADMIN_PHOTO
        super().save(*args, **kwargs)