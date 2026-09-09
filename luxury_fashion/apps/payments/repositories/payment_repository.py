"""
Payment Repository — persistência pura de Payment. Não conhece Asaas, não
interpreta resposta de API, não faz fallback, não decide nada. Recebe os
campos já decididos (pelo service/mapper) e só grava.
"""
from luxury_fashion.apps.payments.models.payment_model import Payment


def create_payment(**fields) -> Payment:
    payment = Payment(**fields)
    payment.full_clean()
    payment.save()
    return payment


def update_payment(payment: Payment, **fields) -> Payment:
    for field, value in fields.items():
        setattr(payment, field, value)
    payment.full_clean()
    payment.save(update_fields=[*fields.keys(), "updated_at"])
    return payment