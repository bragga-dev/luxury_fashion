import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Reviews(models.Model):
  
    class ReviewsChoices(models.IntegerChoices):
        ONE_STAR = 1, _("⭐ 1 Estrela - Péssimo")
        TWO_STARS = 2, _("⭐⭐ 2 Estrelas - Ruim")
        THREE_STARS = 3, _("⭐⭐⭐ 3 Estrelas - Regular")
        FOUR_STARS = 4, _("⭐⭐⭐⭐ 4 Estrelas - Bom")
        FIVE_STARS = 5, _("⭐⭐⭐⭐⭐ 5 Estrelas - Excelente")

    reviews_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item_id = models.OneToOneField("payments.OrderItem", on_delete=models.CASCADE, related_name="reviews")
    user_id = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    reviews = models.PositiveSmallIntegerField(_("Avaliação"), choices=ReviewsChoices.choices, help_text=_("Nota de 1 a 5 estrelas"))
    comment = models.TextField(_("Comentário"), blank=True, null=True, max_length=500, help_text=_("Deixe um comentário sobre sua experiência"))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    is_authorized = models.BooleanField(_("Autorizado"), default=False)

    class Meta:
        verbose_name = _("Avaliação de serviço")
        verbose_name_plural = _("Avaliações de serviços")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order_item_id", "user_id"],
                name="unique_reviews_per_order_item_id_user_id",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["order_item_id"]),
            models.Index(fields=["reviews"]),
        ]

    def __str__(self):
        return f"{self.user_id} → ({self.order_item_id}): {self.reviews}★"

    def clean(self):
        if self.order_item_id_id:
            order = self.order_item_id.order_id
            if order.order_status != order.StatusOrder.COMPLETED:
                raise ValidationError({"order_item_id": _("Só é possível avaliar pedidos concluídos.")})
            if self.user_id_id and self.user_id_id != order.user_id_id:
                raise ValidationError({"user_id": _("Usuário não corresponde ao pedido.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)