import uuid
from datetime import date
from typing import Optional, List
from ninja import Schema, Field
from pydantic import field_validator

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.schemas.client_schema import ClientOut
from enum import Enum



class BrazilianStateEnum(str, Enum):
    AC = "AC" 
    AL = "AL" 
    AP = "AP" 
    AM = "AM"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MT = "MT"
    MS = "MS"
    MG = "MG"
    PA = "PA"
    PB = "PB"
    PR = "PR"
    PE = "PE"
    PI = "PI"
    RJ = "RJ"
    RN = "RN"
    RS = "RS"
    RO = "RO"
    RR = "RR"
    SC = "SC"
    SP = "SP"
    SE = "SE"
    TO = "TO"




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
    items: list[AddressOut]