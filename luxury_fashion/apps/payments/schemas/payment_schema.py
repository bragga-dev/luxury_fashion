import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ninja import Schema, Field

from luxury_fashion.apps.payments.models.payment_model import Payment


class PaymentBillingTypeEnum(str, Enum):
    BOLETO = "BOLETO"
    PIX = "PIX"
    CREDIT_CARD = "CREDIT_CARD"


class PaymentStatusEnum(str, Enum):
    """Espelha Payment.PaymentStatus."""
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    OVERDUE = "OVERDUE"
    REFUNDED = "REFUNDED"
    RECEIVED_IN_CASH = "RECEIVED_IN_CASH"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUND_IN_PROGRESS = "REFUND_IN_PROGRESS"
    CHARGEBACK_REQUESTED = "CHARGEBACK_REQUESTED"
    CHARGEBACK_DISPUTE = "CHARGEBACK_DISPUTE"
    AWAITING_CHARGEBACK_REVERSAL = "AWAITING_CHARGEBACK_REVERSAL"
    DUNNING_REQUESTED = "DUNNING_REQUESTED"
    DUNNING_RECEIVED = "DUNNING_RECEIVED"
    AWAITING_RISK_ANALYSIS = "AWAITING_RISK_ANALYSIS"
    CANCELLED = "CANCELLED"


class CreditCardIn(Schema):
    """Só é usado quando billing_type=CREDIT_CARD. Nunca é persistido."""
    holder_name: str
    number: str
    expiry_month: str
    expiry_year: str
    ccv: str


class CreditCardHolderInfoIn(Schema):
    name: str
    email: str
    cpf_cnpj: str
    postal_code: str
    address_number: str
    phone: Optional[str] = None


class PaymentCreateIn(Schema):
    """
    order_id vem da URL (/orders/{order_id}/payments), não daqui — não
    precisa duplicar. billing_type=CREDIT_CARD exige credit_card e
    credit_card_holder_info; PIX e BOLETO ignoram os dois.
    """
    billing_type: PaymentBillingTypeEnum
    credit_card: Optional[CreditCardIn] = None
    credit_card_holder_info: Optional[CreditCardHolderInfoIn] = None


class RefundIn(Schema):
    """
    Estorno. value ausente = estorno integral. value informado = estorno
    parcial (ex.: reter taxa de cancelamento) — a Asaas valida se cabe no
    saldo disponível da cobrança.
    """
    value: Optional[Decimal] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, max_length=500)


class PaymentOut(Schema):
    payment_id: uuid.UUID
    order_id: uuid.UUID
    asaas_payment_id: Optional[str] = None
    value: Decimal
    billing_type: PaymentBillingTypeEnum
    status: PaymentStatusEnum
    due_date: date
    description: str
    invoice_url: Optional[str] = None
    bank_slip_url: Optional[str] = None
    pix_qr_code: Optional[str] = None
    pix_copy_paste: Optional[str] = None
    payment_date: Optional[datetime] = None
    net_value: Optional[Decimal] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, payment: Payment) -> "PaymentOut":
        return cls(
            payment_id=payment.payment_id,
            order_id=payment.order_id_id,  # _id pega o UUID cru, não o objeto Order
            asaas_payment_id=payment.asaas_payment_id,
            value=payment.value,
            billing_type=payment.billing_type,
            status=payment.status,
            due_date=payment.due_date,
            description=payment.description,
            invoice_url=payment.invoice_url,
            bank_slip_url=payment.bank_slip_url,
            pix_qr_code=payment.pix_qr_code,
            pix_copy_paste=payment.pix_copy_paste,
            payment_date=payment.payment_date,
            net_value=payment.net_value,
            created_at=payment.created_at,
        )


class PaymentFilterIn(Schema):
    """Filtros de listagem (admin)."""
    order_id: Optional[uuid.UUID] = None
    status: Optional[PaymentStatusEnum] = None
    billing_type: Optional[PaymentBillingTypeEnum] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AsaasWebhookIn(Schema):
    """
    Corpo enviado pela Asaas: {"event": "PAYMENT_RECEIVED", "payment": {...}}.
    `payment` fica solto como dict porque o corpo real tem muito mais campo
    do que a gente usa (camelCase, e a Asaas pode adicionar novos sem avisar).
    """
    event: str
    payment: dict