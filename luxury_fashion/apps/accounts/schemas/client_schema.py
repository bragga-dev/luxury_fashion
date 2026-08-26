import uuid
from datetime import date
from typing import Optional
from ninja import Schema, Field
from pydantic import field_validator
import re
from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.schemas.user_schema import UserOut
from luxury_fashion.apps.core.constants.gender import Gender
from phonenumbers import parse, is_valid_number, NumberParseException
from enum import Enum


class GenderEnum(str, Enum):
    MALE = Gender.MALE
    FEMALE = Gender.FEMALE
    OTHER = Gender.OTHER


class ClientOut(Schema):
    client_id: uuid.UUID
    user: UserOut
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None 
    photo_url: Optional[str] = None
    gender: GenderEnum
    gender_label: str
    birth_date: Optional[date] = None  
    asaas_customer_id: Optional[str]
    cpf: Optional[str] = None
    
    @classmethod
    def from_orm(cls, client: Client) -> "ClientOut":
        return cls(
            id=client.id,
            user=UserOut.from_orm(client.user),
            username=client.username,
            first_name=client.first_name,
            last_name=client.last_name,
            instagram=client.instagram,
            phone=str(client.phone) if client.phone else None,  
            gender=client.gender,
            gender_label=client.get_gender_display(),
            birth_date=client.birth_date,
            photo_url=client.photo_url,  
            asaas_customer_id=client.asaas_customer_id,  
            cpf=client.cpf,  
        )


class ClientCreateIn(Schema):
    user_id: uuid.UUID
    username: str = Field(..., min_length=2, max_length=150)
    first_name: str = Field(..., min_length=2, max_length=255)
    last_name: str = Field(..., min_length=2, max_length=255)
    photo_url: Optional[str] = None  
    phone: Optional[str] = None  
    birth_date: Optional[date] = None 
    gender: Optional[GenderEnum] = None
    cpf: Optional[str] = None

    @field_validator("birth_date")
    @classmethod
    def birth_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        return v

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        import re
        if not re.match(r'^[\w.@+-]+$', v):
            raise ValueError("Username inválido. Use apenas letras, números e @/./+/-/_.")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                parsed = parse(v, "BR")
            except NumberParseException:
                raise ValueError("Número de telefone inválido.")
            if not is_valid_number(parsed):
                raise ValueError("Número de telefone inválido.")
        return v


class ClientUpdateIn(Schema):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None  
    cpf: Optional[str] = None 

    @field_validator("birth_date")
    @classmethod
    def birth_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        return v

    @field_validator("username")
    @classmethod
    def username_format(cls, v: Optional[str]) -> Optional[str]:
        if v:
            import re
            if not re.match(r'^[\w.@+-]+$', v):
                raise ValueError("Username inválido. Use apenas letras, números e @/./+/-/_.")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                parsed = parse(v, "BR")
            except NumberParseException:
                raise ValueError("Número de telefone inválido.")
            if not is_valid_number(parsed):
                raise ValueError("Número de telefone inválido.")
        return v