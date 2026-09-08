"""
AsaasCustomer Selectors — queries de leitura.
"""
import uuid
from typing import Optional

from luxury_fashion.apps.payments.models.asaas_customer_model import AsaasCustomer


def get_asaas_customer_by_client_id(client_id: uuid.UUID) -> Optional[AsaasCustomer]:
    return AsaasCustomer.objects.filter(client_id=client_id).first()