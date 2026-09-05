"""
AsaasCustomer Repository — persistência pura do vínculo Client <-> customer
na Asaas. A criação do customer NA Asaas acontece no service
(payment_service), que fala com o AsaasClient; aqui só gravamos o
resultado.
"""
from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.payments.models.asaas_customer_model import AsaasCustomer


def create_asaas_customer(client: Client, asaas_customer_id: str) -> AsaasCustomer:
    asaas_customer = AsaasCustomer(client_id=client, asaas_customer_id=asaas_customer_id)
    asaas_customer.full_clean()
    asaas_customer.save()
    return asaas_customer