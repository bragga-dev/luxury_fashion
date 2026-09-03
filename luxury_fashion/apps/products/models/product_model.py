from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
from django.core.validators import MinValueValidator
from luxury_fashion.apps.core.validators.image_validator import validate_image_file



class Product(models.Model):

    class ProductGender(models.TextChoices):
        MASCULINO = "masculino", _("Masculino")
        FEMININO = "feminino", _("Feminino")
        UNISSEX = "unissex", _("Unissex")

    class ProductSize(models.TextChoices):
        PP = "PP", _("PP")
        P = "P", _("P")
        M = "M", _("M")
        G = "G", _("G")
        GG = "GG", _("GG")
        XGG = "XGG", _("XGG")

        G1 = "G1", _("G1")
        G2 = "G2", _("G2")
        G3 = "G3", _("G3")
        G4 = "G4", _("G4")
        G5 = "G5", _("G5")
        G6 = "G6", _("G6")

        SIZE_34 = "34", _("34")
        SIZE_36 = "36", _("36")
        SIZE_38 = "38", _("38")
        SIZE_40 = "40", _("40")
        SIZE_42 = "42", _("42")
        SIZE_44 = "44", _("44")
        SIZE_46 = "46", _("46")
        SIZE_48 = "48", _("48")
        SIZE_50 = "50", _("50")
        SIZE_52 = "52", _("52")
        SIZE_54 = "54", _("54")
        SIZE_56 = "56", _("56")
        SIZE_58 = "58", _("58")
        SIZE_60 = "60", _("60")
        SIZE_62 = "62", _("62")
        SIZE_64 = "64", _("64")


    class ProductColor(models.TextChoices):
        BLACK = "black", _("Preto")
        WHITE = "white", _("Branco")
        RED = "red", _("Vermelho")
        BLUE = "blue", _("Azul")
        GREEN = "green", _("Verde")
        PINK = "pink", _("Rosa")
        YELLOW = "yellow", _("Amarelo")
        ORANGE = "orange", _("Laranja")
        PURPLE = "purple", _("Roxo")
        BROWN = "brown", _("Marrom")
        BEIGE = "beige", _("Bege")
        GRAY = "gray", _("Cinza")
        NAVY = "navy", _("Azul-marinho")
        WINE = "wine", _("Vinho")
        OFF_WHITE = "off_white", _("Off-White")


    product_category_id = models.ForeignKey("products.ProductCategory", on_delete=models.PROTECT, related_name="product_category")
    product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(_("Nome"), max_length=100, blank=False, null=False)
   
    is_active = models.BooleanField(_("Ativa?"), default=True)
    created_at = models.DateTimeField(_("Criada em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizada em"), auto_now=True)

    class Meta:
        verbose_name = _("Produto")
        verbose_name_plural = _("Produtos")
        ordering = ["product_name"]

    def __str__(self):
        return f"{self.product_name}"

  