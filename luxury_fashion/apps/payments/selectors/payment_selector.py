"""
Payment Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.payments.models.payment_model import Payment


def get_payment_by_id(payment_id: uuid.UUID) -> Optional[Payment]:
    return Payment.objects.select_related("order_id").filter(payment_id=payment_id).first()


def get_payment_by_id_and_user(payment_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Payment]:
    """Garante que a cobrança pertence a um pedido do próprio usuário."""
    return (
        Payment.objects.select_related("order_id")
        .filter(payment_id=payment_id, order_id__user_id=user_id)
        .first()
    )


def get_payment_by_asaas_id(asaas_payment_id: str) -> Optional[Payment]:
    return Payment.objects.select_related("order_id").filter(asaas_payment_id=asaas_payment_id).first()


def get_payments_by_order(order_id: uuid.UUID) -> QuerySet[Payment]:
    return Payment.objects.filter(order_id=order_id).order_by("-created_at")


def get_open_payment_for_order(order_id: uuid.UUID) -> Optional[Payment]:
    """
    Cobrança em aberto (pendente ou em análise) pro pedido — usado pra
    evitar criar uma segunda cobrança enquanto já existe uma ativa.
    """
    open_statuses = [Payment.PaymentStatus.PENDING, Payment.PaymentStatus.AWAITING_RISK_ANALYSIS]
    return Payment.objects.filter(order_id=order_id, status__in=open_statuses).order_by("-created_at").first()