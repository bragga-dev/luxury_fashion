from typing import Optional
from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.schemas.address_schema import BrazilianStateEnum


def create_address(
    client_id: Client,
    cep: Optional[str] = None,
    street: Optional[str] = None,
    number: Optional[str] = None,
    complement: Optional[str]  = None,
    neighborhood: Optional[str] = None,
    city: Optional[str] = None,
    state: BrazilianStateEnum = None,
    country: Optional[str] = None,
   
) -> AddressesClient:
    fields = {
        "cep": cep,
        "street": street,
        "number": number,
        "complement": complement,
        "neighborhood": neighborhood,
        "city": city,
        "state": state,
        "country": country,
    }
    fields = {k: v for k, v in fields.items() if v is not None}

    address = AddressesClient(client_id=client_id, **fields)
    address.save()
    return address




def update_address(address: AddressesClient, **fields) -> AddressesClient:
    for attr, value in fields.items():
        if value is not None:
            setattr(address, attr, value)
    address.full_clean()   
    address.save()
    return address


def delete_address(address: AddressesClient) -> None:
    address.delete()


def update_status_address_up(address: AddressesClient) -> AddressesClient:
    address.is_preferential = True
    address.save(update_fields=["is_preferential"])
    return address


def update_status_address_down(address: AddressesClient) -> AddressesClient:
    address.is_preferential = False
    address.save(update_fields=["is_preferential"])
    return address