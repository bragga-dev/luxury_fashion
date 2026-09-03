"""
User Selectors — queries de leitura para User.
Nenhuma escrita acontece aqui.
"""
import uuid
from datetime import datetime
from typing import Optional
from django.db.models import QuerySet, Q
from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient


# ── Busca individual ──────────────────────────────────────────────────────────

def get_address_by_id(address_id: uuid.UUID) -> Optional[AddressesClient]:
    """Busca endereço por ID."""
    return AddressesClient.objects.filter(address_id=address_id).first()


def get_address_by_client(client_id: uuid.UUID) -> Optional[AddressesClient]:
    """Busca endereço por cliente)."""
    return AddressesClient.objects.filter(client_id=client_id).all()

def get_address_is_preferential(client_id, is_preferential: bool = True) -> Optional['AddressesClient']:
    """Retorna um endereço preferencial de um cliente específico"""
    return AddressesClient.objects.filter(client_id=client_id, is_preferential=is_preferential).select_related('client_id').first()

# ── Verificações de existência ────────────────────────────────────────────────

def address_exists(address_id: uuid.UUID) -> bool:
    """Verifica se endereço existe."""
    return AddressesClient.objects.filter(address_id=address_id).exists()


# ── Listagens ─────────────────────────────────────────────────────────────────

def get_all_addresses() -> QuerySet[AddressesClient]:
    """Retorna todos os endereços."""
    return AddressesClient.objects.all()

# ── Busca por estado ─────────────────────────────────────────────────────────────────

def get_addresses_by_state(state: str) -> QuerySet[AddressesClient]:
    """Retorna endereços de um estado específico."""
    return AddressesClient.objects.filter(state=state).select_related('client_id')

def get_addresses_by_city(city: str) -> QuerySet[AddressesClient]:
    """Retorna endereços de uma cidade específica."""
    return AddressesClient.objects.filter(city__icontains=city).select_related('client_id')

def get_addresses_by_state_and_city(state: str, city: str) -> QuerySet[AddressesClient]:
    """Retorna endereços por estado e cidade."""
    return AddressesClient.objects.filter(
        state=state,
        city__icontains=city
    ).select_related('client_id')

# ── Busca por cep ─────────────────────────────────────────────────────────────────

def get_addresses_by_cep(cep: str) -> QuerySet[AddressesClient]:
    """Retorna endereços por CEP (busca exata)."""
    return AddressesClient.objects.filter(cep=cep).select_related('client_id')

def get_addresses_by_cep_partial(cep_prefix: str) -> QuerySet[AddressesClient]:
    """Retorna endereços por prefixo do CEP."""
    return AddressesClient.objects.filter(cep__startswith=cep_prefix).select_related('client_id')

# ── Contagem ─────────────────────────────────────────────────────────────────

def count_addresses_by_client(client_id: uuid.UUID) -> int:
    """Conta quantos endereços um cliente possui."""
    return AddressesClient.objects.filter(client_id=client_id).count()