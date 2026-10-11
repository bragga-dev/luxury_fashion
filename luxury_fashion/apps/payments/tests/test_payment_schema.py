"""
Testes de schema — validações de entrada isoladas do banco e da Asaas.
"""
import pytest
from pydantic import ValidationError

from luxury_fashion.apps.payments.schemas.payment_schema import (
    PaymentBillingTypeEnum,
    PaymentCreateIn,
    RefundIn,
)


class TestPaymentCreateIn:
    def test_pix_does_not_require_credit_card(self):
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)
        assert payload.credit_card is None
        assert payload.credit_card_holder_info is None

    def test_boleto_does_not_require_credit_card(self):
        payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.BOLETO)
        assert payload.credit_card is None

    def test_credit_card_requires_card_and_holder_info(self):
        with pytest.raises(ValidationError):
            PaymentCreateIn(billing_type=PaymentBillingTypeEnum.CREDIT_CARD)

    def test_credit_card_requires_holder_info_even_with_card(self):
        with pytest.raises(ValidationError):
            PaymentCreateIn(
                billing_type=PaymentBillingTypeEnum.CREDIT_CARD,
                credit_card={
                    "holder_name": "Maria Silva",
                    "number": "4111111111111111",
                    "expiry_month": "12",
                    "expiry_year": "2030",
                    "ccv": "123",
                },
            )

    def test_credit_card_with_both_fields_is_valid(self):
        payload = PaymentCreateIn(
            billing_type=PaymentBillingTypeEnum.CREDIT_CARD,
            credit_card={
                "holder_name": "Maria Silva",
                "number": "4111111111111111",
                "expiry_month": "12",
                "expiry_year": "2030",
                "ccv": "123",
            },
            credit_card_holder_info={
                "name": "Maria Silva",
                "email": "maria@example.com",
                "cpf_cnpj": "39053344705",
                "postal_code": "45200000",
                "address_number": "100",
            },
        )
        assert payload.credit_card.holder_name == "Maria Silva"
        assert payload.credit_card_holder_info.cpf_cnpj == "39053344705"


class TestRefundIn:
    def test_defaults_to_full_refund(self):
        payload = RefundIn()
        assert payload.value is None
        assert payload.description is None

    def test_value_must_be_positive(self):
        with pytest.raises(ValidationError):
            RefundIn(value=0)

    def test_negative_value_is_rejected(self):
        with pytest.raises(ValidationError):
            RefundIn(value=-5)

    def test_partial_refund_with_description(self):
        payload = RefundIn(value=10, description="Taxa de cancelamento retida")
        assert payload.value == 10
        assert payload.description == "Taxa de cancelamento retida"
