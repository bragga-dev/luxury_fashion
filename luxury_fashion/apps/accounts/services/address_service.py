from uuid import UUID
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.repositories.addresses_repository import (
    create_address,
    update_address,
    update_status_address_down,
    update_status_address_up,
)
from luxury_fashion.apps.accounts.repositories.client_repository import (
    remove_client_photo,
    set_client_photo,
)
from luxury_fashion.apps.accounts.schemas.address_schema import (
    AddressCreateIn,
    AddressOut,
    AddressesList,
    AddressUpdateIn,
)
from luxury_fashion.apps.accounts.selectors.address_selector import (
    get_address_by_id,
    get_address_is_preferential,
    get_address_by_client,  # Adicionar este import
    count_addresses_by_client,  # Adicionar este import
)
from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.core.exceptions.address import AddressNotFound
from luxury_fashion.apps.core.exceptions.permissions import ClientNotFoundError, PermissionDenied
from luxury_fashion.apps.core.exceptions.user import UserNotFound


def _get_own_client_address(user_id: UUID, address_id: UUID) -> AddressesClient:
    """
    Resolve o Client dono do endereço e garante que pertence a ele.
    Função privada reutilizada por várias operações.
    """
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    address = get_address_by_id(address_id=address_id)
    if address is None or address.client_id != client.client_id:
        raise AddressNotFound()
    return address


def _get_client_by_user_id_or_raise(user_id: UUID):
    """Helper para buscar cliente ou levantar exceção."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise UserNotFound()
    return client


# ── Operações de Escrita ──────────────────────────────────────────────────

def register_address_for_client(user_id: UUID, data: AddressCreateIn) -> AddressOut:
    """Registra um novo endereço para o cliente."""
    client = _get_client_by_user_id_or_raise(user_id)
    
    address = create_address(
        client_id=client.client_id,
        cep=data.cep,
        street=data.street,
        number=data.number,
        complement=data.complement,
        neighborhood=data.neighborhood,
        city=data.city,
        state=data.state,
        country=data.country,
    )
    return AddressOut.from_orm(address)


def update_address_for_client(user_id: UUID, address_id: UUID, payload: AddressUpdateIn) -> AddressOut:
    """Atualiza um endereço existente do cliente."""
    address = _get_own_client_address(user_id=user_id, address_id=address_id)
    address = update_address(
        address=address,
        cep=payload.cep,
        street=payload.street,
        number=payload.number,
        complement=payload.complement,
        neighborhood=payload.neighborhood,
        city=payload.city,
        state=payload.state,
        country=payload.country,
    )
    return AddressOut.from_orm(address)


def update_address_check_up(user_id: UUID, address_id: UUID) -> AddressOut:
    """Ativa (check up) um endereço."""
    address = _get_own_client_address(user_id=user_id, address_id=address_id)
    address = update_status_address_up(address)
    return AddressOut.from_orm(address)


def update_address_check_down(user_id: UUID, address_id: UUID) -> AddressOut:
    """Desativa (check down) um endereço."""
    address = _get_own_client_address(user_id=user_id, address_id=address_id)
    address = update_status_address_down(address)
    return AddressOut.from_orm(address)


# ── Operações de Leitura (Corrigidas) ──────────────────────────────────

def get_address_for_client(user_id: UUID, address_id: UUID) -> AddressOut:
    """
    Busca um endereço específico do cliente.
    Valida se o endereço pertence ao cliente.
    """
    address = _get_own_client_address(user_id=user_id, address_id=address_id)
    return AddressOut.from_orm(address)


def get_preferential_address_for_client(user_id: UUID, is_preferential: bool = True) -> Optional[AddressOut]:
    """
    Busca o endereço preferencial do cliente.
    
    Args:
        user_id: ID do usuário
        is_preferential: Se True busca preferencial, se False busca não-preferencial
    
    Returns:
        AddressOut se encontrar, None se não houver endereço preferencial
    """
    # 1. Busca o cliente
    client = _get_client_by_user_id_or_raise(user_id)
    
    # 2. Busca o endereço preferencial do cliente
    address = get_address_is_preferential(
        client_id=client.client_id,
        is_preferential=is_preferential
    )
    
    # 3. Retorna None se não encontrou
    if address is None:
        return None
    
    # 4. Converte para o schema de saída
    return AddressOut.from_orm(address)


def get_preferential_address_for_client_or_raise(user_id: UUID, is_preferential: bool = True) -> AddressOut:
    """
    Busca o endereço preferencial do cliente ou levanta exceção.
    
    Raises:
        AddressNotFound: Se não houver endereço preferencial
    """
    result = get_preferential_address_for_client(user_id, is_preferential)
    if result is None:
        raise AddressNotFound("Cliente não possui endereço preferencial")
    return result


def get_addresses_for_client(user_id: UUID) -> list[AddressOut]:
    """
    Retorna todos os endereços do cliente.
    
    Returns:
        Lista de AddressOut (pode ser vazia)
    """
    # 1. Busca o cliente
    client = _get_client_by_user_id_or_raise(user_id)
    
    # 2. Busca todos os endereços do cliente
    addresses = get_address_by_client(client_id=client.client_id)
    
    # 3. Converte para lista de AddressOut
    return [AddressOut.from_orm(address) for address in addresses]


def get_addresses_count_for_client(user_id: UUID) -> int:
    """
    Retorna a quantidade de endereços do cliente.
    """
    client = _get_client_by_user_id_or_raise(user_id)
    return count_addresses_by_client(client_id=client.client_id)


def get_default_address_for_client(user_id: UUID) -> Optional[AddressOut]:
    """
    Busca o endereço padrão do cliente (preferencial).
    Se não houver preferencial, retorna o primeiro endereço.
    """
    # 1. Tenta buscar preferencial
    preferential = get_preferential_address_for_client(user_id)
    if preferential:
        return preferential
    
    # 2. Se não tem preferencial, pega o primeiro
    addresses = get_addresses_for_client(user_id)
    if addresses:
        return addresses[0]
    
    # 3. Cliente não tem nenhum endereço
    return None


def get_default_address_for_client_or_raise(user_id: UUID) -> AddressOut:
    """
    Busca o endereço padrão do cliente ou levanta exceção.
    """
    address = get_default_address_for_client(user_id)
    if address is None:
        raise AddressNotFound("Cliente não possui endereços cadastrados")
    return address


# ── Funções de Validação ──────────────────────────────────────────────────

def validate_address_belongs_to_client(user_id: UUID, address_id: UUID) -> bool:
    """
    Verifica se um endereço pertence a um cliente.
    
    Returns:
        True se pertence, False caso contrário
    """
    try:
        _get_own_client_address(user_id, address_id)
        return True
    except (ClientNotFoundError, AddressNotFound):
        return False