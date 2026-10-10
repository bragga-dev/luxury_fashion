import re

from ninja import Schema
from pydantic import field_validator


class CartShippingQuoteIn(Schema):
    recipient_cep: str

    @field_validator("recipient_cep")
    @classmethod
    def cep_format(cls, v: str) -> str:
        cep = re.sub(r"\D", "", v)
        if len(cep) != 8:
            raise ValueError("O CEP de destino deve possuir 8 dígitos.")
        return cep