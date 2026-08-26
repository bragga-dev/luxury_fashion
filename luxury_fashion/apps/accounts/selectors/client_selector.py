"""
Queries de Cliente - Funções para buscar e filtrar clientes.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from django.db.models import Q, QuerySet, Count, Avg, Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from phonenumbers import parse, is_valid_number, PhoneNumberType
from phonenumbers import parse, format_number, PhoneNumberFormat
import re

from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.constants.gender import Gender


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_client_by_id(client_id: UUID) -> Optional[Client]:
    """
    Retorna cliente pelo ID.
    
    Args:
        client_id: UUID do cliente
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    try:
        return Client.objects.get(client_id=client_id)
    except Client.DoesNotExist:
        return None


def get_client_or_404(client_id: UUID) -> Client:
    """
    Retorna cliente pelo ID ou levanta 404.
    
    Args:
        client_id: UUID do cliente
        
    Returns:
        Client: Cliente encontrado
        
    Raises:
        Http404: Se o cliente não existir
    """
    return get_object_or_404(Client, client_id=client_id)


def get_client_by_user_id(user_id: UUID) -> Optional[Client]:
    """
    Retorna cliente pelo ID do usuário associado.
    
    Args:
        user_id: UUID do usuário
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    try:
        return Client.objects.get(user_id=user_id)
    except Client.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Username
# ═══════════════════════════════════════════════════════════════════════════════

def get_client_by_username(username: str, case_sensitive: bool = False) -> Optional[Client]:
    """
    Retorna cliente pelo username (exato).
    
    Args:
        username: Nome de usuário
        case_sensitive: Se True, busca case-sensitive
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    if not username:
        return None
    
    if case_sensitive:
        return Client.objects.filter(username=username).first()
    return Client.objects.filter(username__iexact=username).first()


def get_clients_by_username_partial(username: str) -> List[Client]:
    """
    Retorna clientes que contenham o username (busca parcial).
    
    Args:
        username: Parte do nome de usuário
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not username:
        return []
    
    return Client.objects.filter(username__icontains=username).select_related('user')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Nome
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients_by_first_name(first_name: str, exact: bool = False) -> List[Client]:
    """
    Retorna clientes pelo primeiro nome.
    
    Args:
        first_name: Primeiro nome
        exact: Se True, busca exata; False busca contém
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not first_name:
        return []
    
    if exact:
        return Client.objects.filter(first_name__iexact=first_name).select_related('user_id')
    return Client.objects.filter(first_name__icontains=first_name).select_related('user_id')


def get_clients_by_last_name(last_name: str, exact: bool = False) -> List[Client]:
    """
    Retorna clientes pelo sobrenome.
    
    Args:
        last_name: Sobrenome
        exact: Se True, busca exata; False busca contém
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not last_name:
        return []
    
    if exact:
        return Client.objects.filter(last_name__iexact=last_name).select_related('user_id')
    return Client.objects.filter(last_name__icontains=last_name).select_related('user_id')


def get_clients_by_full_name(full_name: str) -> List[Client]:
    """
    Retorna clientes pelo nome completo (busca em first_name OU last_name).
    
    Args:
        full_name: Nome completo ou parte dele
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not full_name:
        return []
    
    name_parts = full_name.strip().split()
    
    if len(name_parts) == 1:
        return Client.objects.filter(
            Q(first_name__icontains=full_name) | 
            Q(last_name__icontains=full_name)
        ).select_related('user_id')
    else:
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
        
        return Client.objects.filter(
            Q(first_name__icontains=first_name) & 
            Q(last_name__icontains=last_name)
        ).select_related('user_id')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Email (via User)
# ═══════════════════════════════════════════════════════════════════════════════

def get_client_by_email(email: str) -> Optional[Client]:
    """
    Retorna cliente pelo email do usuário associado.
    
    Args:
        email: Email do usuário
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    if not email:
        return None
    
    try:
        return Client.objects.select_related('user_id').get(user__email__iexact=email)
    except Client.DoesNotExist:
        return None


def get_clients_by_email_partial(email: str) -> List[Client]:
    """
    Retorna clientes por parte do email.
    
    Args:
        email: Parte do email
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not email:
        return []
    
    return Client.objects.filter(user__email__icontains=email).select_related('user_id')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Telefone (PhoneNumberField)
# ═══════════════════════════════════════════════════════════════════════════════

def get_client_by_phone(phone: str) -> Optional[Client]:
    """
    Retorna cliente pelo telefone (formato internacional ou local).
    
    Args:
        phone: Número de telefone (ex: +5511999998888 ou 11999998888)
        
    Returns:
        Optional[Client]: Cliente encontrado ou None
    """
    if not phone:
        return None
    
    import re
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    try:
        parsed = parse(clean_phone, "BR")
        e164 = format_number(parsed, PhoneNumberFormat.E164)
        return Client.objects.filter(phone=e164).first()
    except:
        return Client.objects.filter(phone__contains=clean_phone).first()


def get_clients_by_phone_partial(phone: str) -> List[Client]:
    """
    Retorna clientes que contenham parte do telefone.
    
    Args:
        phone: Parte do número de telefone
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not phone:
        return []
    
    clean_phone = re.sub(r'[^\d+]', '', phone)
    return Client.objects.filter(phone__contains=clean_phone).select_related('user_id')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Data de Nascimento
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients_by_birth_date(birth_date: date) -> List[Client]:
    """
    Retorna clientes com data de nascimento específica.
    
    Args:
        birth_date: Data de nascimento
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not birth_date:
        return []
    
    return Client.objects.filter(birth_date=birth_date).select_related('user_id')


def get_clients_by_birth_date_range(start_date: date, end_date: date) -> List[Client]:
    """
    Retorna clientes com data de nascimento em um intervalo.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not start_date or not end_date:
        return []
    
    return Client.objects.filter(
        birth_date__gte=start_date,
        birth_date__lte=end_date
    ).select_related('user_id')


def get_clients_with_birthday_today() -> List[Client]:
    """
    Retorna clientes que fazem aniversário hoje.
    
    Returns:
        List[Client]: Lista de clientes aniversariantes
    """
    today = date.today()
    return Client.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day
    ).select_related('user_id')


def get_clients_with_birthday_in_month(month: int) -> List[Client]:
    """
    Retorna clientes que fazem aniversário em um mês específico.
    
    Args:
        month: Mês (1-12)
        
    Returns:
        List[Client]: Lista de clientes aniversariantes
    """
    if not 1 <= month <= 12:
        return []
    return Client.objects.filter(birth_date__month=month).select_related('user_id').order_by('birth_date__day')


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Gênero
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients_by_gender(gender: str) -> List[Client]:
    """
    Retorna clientes por gênero.
    
    Args:
        gender: Gênero (Gender.MALE, Gender.FEMALE, Gender.OTHER)
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not gender:
        return []
    
    return Client.objects.filter(gender=gender).select_related('user_id')


def get_gender_statistics() -> Dict[str, int]:
    """
    Retorna estatísticas de gênero dos clientes.
    
    Returns:
        Dict: { 'MALE': 10, 'FEMALE': 15, 'OTHER': 5 }
    """
    stats = {}
    for gender_choice in Gender.CHOICES:
        gender_code = gender_choice[0]
        count = Client.objects.filter(gender=gender_code).count()
        stats[gender_code] = count
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Combinadas
# ═══════════════════════════════════════════════════════════════════════════════

def search_clients(query: str, search_fields: List[str] = None,) -> List[Client]:
    """
    Busca clientes em múltiplos campos.
    
    Args:
        query: Termo de busca
        search_fields: Campos para buscar (default: username, first_name, last_name, email
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not query:
        return []
    
    if search_fields is None:
        search_fields = ['username', 'first_name', 'last_name', 'user__email']    
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": query})
    
    return Client.objects.filter(q_objects).select_related('user_id')


def get_clients_by_name_and_username(name: Optional[str] = None, username: Optional[str] = None,) -> List[Client]:
    """
    Busca clientes por nome E/OU username.
    
    Args:
        name: Nome (busca parcial em first_name e last_name)
        username: Username (busca parcial)
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    q = Q()
    
    if name:
        q &= Q(first_name__icontains=name) | Q(last_name__icontains=name)
    
    if username:
        q &= Q(username__icontains=username)
    
    if not q:
        return []
    
    return Client.objects.filter(q).select_related('user_id')


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_clients(
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    gender: Optional[str] = None,
    created_after: Optional[date] = None,
    created_before: Optional[date] = None,
    birth_date_after: Optional[date] = None,
    birth_date_before: Optional[date] = None,
    has_phone: Optional[bool] = None,
    has_cpf: Optional[bool] = None,
    has_photo: Optional[bool] = None,
    order_by: str = 'first_name',
) -> List[Client]:
    """
    Filtra clientes com múltiplos critérios.
    
    Args:
        is_active: Filtrar por status ativo
        is_verified: Filtrar por verificação de email
        gender: Filtrar por gênero
        created_after: Criados após esta data
        created_before: Criados antes desta data
        birth_date_after: Data de nascimento após
        birth_date_before: Data de nascimento antes
        has_phone: Tem telefone cadastrado
        has_instagram: Tem Instagram cadastrado
        has_photo: Tem foto cadastrada
        order_by: Campo para ordenação
        
    Returns:
        List[Client]: Lista de clientes filtrados
    """
    q = Q()
    
    # Filtros do User
    if is_active is not None:
        q &= Q(user__is_active=is_active)
    
    if is_verified is not None:
        q &= Q(user__is_trusty=is_verified)
    
    # Filtros do Client
    if gender:
        q &= Q(gender=gender)
    
    if created_after:
        q &= Q(user__date_joined__gte=created_after)
    
    if created_before:
        q &= Q(user__date_joined__lte=created_before)
    
    if birth_date_after:
        q &= Q(birth_date__gte=birth_date_after)
    
    if birth_date_before:
        q &= Q(birth_date__lte=birth_date_before)
    
    if has_phone is not None:
        if has_phone:
            q &= Q(phone__isnull=False) & ~Q(phone='')
        else:
            q &= Q(phone__isnull=True) | Q(phone='')
    
    if has_cpf is not None:
        if has_cpf:
            q &= Q(instagram__isnull=False) & ~Q(instagram='')
        else:
            q &= Q(instagram__isnull=True) | Q(instagram='')
    
    if has_photo is not None:
        if has_photo:
            q &= ~Q(photo='default/client_img.jpg') & Q(photo__isnull=False)
        else:
            q &= Q(photo='default/client_img.jpg') | Q(photo__isnull=True)
    
    if not q:
        return []
    
    return Client.objects.filter(q).select_related('user_id').order_by(order_by)



# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_client_exists(client_id: UUID) -> bool:
    """
    Verifica se um cliente existe.
    
    Args:
        client_id: UUID do cliente
        
    Returns:
        bool: True se existir, False caso contrário
    """
    return Client.objects.filter(id=client_id).exists()


def get_client_full_name_display(client: Client) -> str:
    """
    Retorna o nome completo do cliente para exibição.
    
    Args:
        client: Instância do cliente
        
    Returns:
        str: Nome completo formatado
    """
    if client.first_name and client.last_name:
        return f"{client.first_name} {client.last_name}"
    elif client.first_name:
        return client.first_name
    elif client.last_name:
        return client.last_name
    return client.username or client.user.email


def get_client_contact_info(client: Client) -> Dict[str, Optional[str]]:
    """
    Retorna informações de contato do cliente.
    
    Args:
        client: Instância do cliente
        
    Returns:
        Dict: Informações de contato
    """
    return {
        'email': client.user.email if client.user else None,
        'phone': str(client.phone) if client.phone else None,
    }


def normalize_phone_for_search(phone: str) -> str:
    """
    Normaliza um número de telefone para busca.
    
    Args:
        phone: Número de telefone
        
    Returns:
        str: Número normalizado no formato E.164
    """
    
    
    if not phone:
        return ''
    
    import re
    clean = re.sub(r'[^\d+]', '', phone)
    
    try:
        parsed = parse(clean, "BR")
        return format_number(parsed, PhoneNumberFormat.E164)
    except:
        return clean


# ═══════════════════════════════════════════════════════════════════════════════
# Bulk Operations
# ═══════════════════════════════════════════════════════════════════════════════

def get_clients_by_ids(client_ids: List[UUID]) -> List[Client]:
    """
    Retorna múltiplos clientes por IDs.
    
    Args:
        client_ids: Lista de UUIDs
        
    Returns:
        List[Client]: Lista de clientes encontrados
    """
    if not client_ids:
        return []
    
    return Client.objects.filter(id__in=client_ids).select_related('user_id')


def get_clients_without_phone() -> List[Client]:
    """
    Retorna clientes sem telefone cadastrado.
    
    Returns:
        List[Client]: Lista de clientes sem telefone
    """
    return Client.objects.filter(Q(phone__isnull=True) | Q(phone='')).select_related('user_id')


def get_clients_without_instagram() -> List[Client]:
    """
    Retorna clientes sem Instagram cadastrado.
    
    Returns:
        List[Client]: Lista de clientes sem Instagram
    """
    return Client.objects.filter(Q(instagram__isnull=True) | Q(instagram='')).select_related('user_id')


