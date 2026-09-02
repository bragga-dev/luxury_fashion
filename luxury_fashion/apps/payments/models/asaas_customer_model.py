
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
from django.core.validators import MinValueValidator
from luxury_fashion.apps.core.utils.generate_random_code import generate_random_code











class AsaasCustomer(models.Model):
    user_id = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="asaas_customer")
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asaas_customer_id = models.CharField(_("ID do cliente na Asaas"), max_length=50, blank=True, null=True, db_index=True)
