from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class AsaasCustomer(models.Model):
    client_id = models.OneToOneField("accounts.Client", on_delete=models.CASCADE, related_name="asaas_customer")
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asaas_customer_id = models.CharField(_("ID do cliente na Asaas"), unique=True, max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client_id.get_full_name()} x {self.asaas_customer_id}"