import uuid
from datetime import date
from typing import Optional
from ninja import Schema


from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.schemas.user_schema import UserOut
from luxury_fashion.apps.accounts.schemas.client_schema import GenderEnum



class ClientProfileOut(Schema):
    client_id: uuid.UUID
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    gender: GenderEnum
    gender_label: str
    birth_date: Optional[date] = None
    cpf: Optional[str] = None

    @classmethod
    def from_orm(cls, client: Client) -> "ClientProfileOut":
        return cls(
            id=client.id,
            username=client.username,
            first_name=client.first_name,
            last_name=client.last_name,
            phone=str(client.phone) if client.phone else None,
            gender=client.gender,
            gender_label=client.get_gender_display(),
            birth_date=client.birth_date,
            photo_url=client.photo_url,
            cpf=client.cpf,
        )


class MeOut(Schema):
    user:     UserOut
    client:   Optional[ClientProfileOut]   = None
   

    @classmethod
    def from_user(cls, user: User) -> "MeOut":
        client   = getattr(user, "client_profile", None)
        return cls(
            user=UserOut.from_orm(user),
            client=ClientProfileOut.from_orm(client) if client else None,
            
        )
