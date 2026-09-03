import uuid
from datetime import date
from typing import Optional, List
from ninja import Schema, Field
from pydantic import field_validator

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.schemas.client_schema import ClientOut
from enum import Enum



class BrazilianStateEnum(str, Enum):
    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"




class AddressOut(Schema):
    client: ClientOut
    address_id: uuid.UUID
    cep: str
    street: str
    number: str
    complement: str 
    neighborhood: str
    city: str
    state: BrazilianStateEnum
    country: str 
    is_preferential: bool

    @classmethod
    def from_orm(cls, address: AddressesClient) -> "AddressesClient":
        return cls(
            address_id=address.address_id,
            client=ClientOut.from_orm(address.client),
            cep=address.cep,
            street=address.street,
            number=address.number,
            complement=address.complement,
            neighborhood=address.neighborhood,         
            city=address.city,
            state=address.state,
            state_label=address.get_state_display(),
            country=address.country,
            is_preferential=address.is_preferential,  
           
        )


class AddressCreateIn(Schema):
    client_id: uuid.UUID
    cep: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str]  = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None 
    state: BrazilianStateEnum = None
    country: Optional[str] = None

class AddressUpdateIn(Schema):
    cep: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str]  = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None 
    state: BrazilianStateEnum = None
    country: Optional[str] = None



class AddressesList(Schema):
    items: list[AddressesOut]