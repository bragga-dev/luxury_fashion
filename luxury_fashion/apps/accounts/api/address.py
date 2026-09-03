"""
Address endpoints — CRUD de endereços para clientes.
"""
import uuid
from typing import Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router


from luxury_fashion.apps.accounts.schemas.user_schema import MessageOut

from luxury_fashion.apps.accounts.schemas.address_schema import (
    AddressCreateIn,
    AddressOut,
    AddressUpdateIn,
    
)
from luxury_fashion.apps.accounts.services.address_service import (
    register_address_for_client,
    update_address_for_client,
    update_address_check_up,
    update_address_check_down,
    get_address_for_client,
    get_preferential_address_for_client,
    get_addresses_for_client,
    get_default_address_for_client,
    get_addresses_count_for_client,
    validate_address_belongs_to_client,
)
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions.address import AddressNotFound
from luxury_fashion.apps.core.exceptions.permissions import ClientNotFoundError
from luxury_fashion.apps.core.exceptions.user import UserNotFound
from luxury_fashion.apps.core.permissions.auth_classes import ClientOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset

router = Router()


# ── Listagem ──────────────────────────────────────────────────────────────────

@router.get(
    "/my-addresses",
    response={200: list[AddressOut], 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Lista todos os endereços do cliente logado",
    description=(
        "Retorna todos os endereços cadastrados para o cliente autenticado. "
        "Se o cliente não tiver endereços, retorna uma lista vazia."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_addresses_router(request):
    """
    Lista todos os endereços do cliente autenticado.
    """
    try:
        user: User = request.auth
        addresses = get_addresses_for_client(user_id=user.id)
        return 200, addresses
    except UserNotFound as e:
        return 404, {"detail": str(e)}


@router.get(
    "/my-addresses/count",
    response={200: dict, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Conta quantos endereços o cliente possui",
    description=(
        "Retorna a quantidade total de endereços cadastrados para o cliente autenticado."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def count_my_addresses_router(request):
    """
    Conta quantos endereços o cliente possui.
    """
    try:
        user: User = request.auth
        count = get_addresses_count_for_client(user_id=user.id)
        return 200, {"count": count}
    except UserNotFound as e:
        return 404, {"detail": str(e)}


# ── Busca Individual ──────────────────────────────────────────────────────────

@router.get(
    "/my-addresses/{address_id}",
    response={200: AddressOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Detalhe de um endereço específico",
    description=(
        "Retorna os detalhes de um endereço específico do cliente autenticado. "
        "Valida se o endereço realmente pertence ao cliente."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def detail_my_address_router(request, address_id: uuid.UUID):
    """
    Busca um endereço específico do cliente autenticado.
    """
    try:
        user: User = request.auth
        address = get_address_for_client(
            user_id=user.id,
            address_id=address_id
        )
        return 200, address
    except (UserNotFound, AddressNotFound) as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}


@router.get(
    "/my-addresses/preferential",
    response={200: AddressOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Busca o endereço preferencial do cliente",
    description=(
        "Retorna o endereço marcado como preferencial do cliente autenticado. "
        "Se não houver endereço preferencial, retorna 404."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_preferential_address_router(request):
    """
    Busca o endereço preferencial do cliente autenticado.
    """
    try:
        user: User = request.auth
        address = get_preferential_address_for_client(user_id=user.id)
        if address is None:
            return 404, {"detail": "Nenhum endereço preferencial encontrado."}
        return 200, address
    except UserNotFound as e:
        return 404, {"detail": str(e)}


@router.get(
    "/my-addresses/default",
    response={200: AddressOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Busca o endereço padrão do cliente",
    description=(
        "Retorna o endereço preferencial do cliente. Se não houver preferencial, "
        "retorna o primeiro endereço cadastrado. Se não houver nenhum endereço, retorna 404."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_default_address_router(request):
    """
    Busca o endereço padrão do cliente (preferencial ou primeiro cadastrado).
    """
    try:
        user: User = request.auth
        address = get_default_address_for_client(user_id=user.id)
        if address is None:
            return 404, {"detail": "Nenhum endereço cadastrado."}
        return 200, address
    except UserNotFound as e:
        return 404, {"detail": str(e)}


# ── Criação ────────────────────────────────────────────────────────────────────

@router.post(
    "/my-addresses",
    response={201: AddressOut, 400: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cadastra um novo endereço para o cliente",
    description=(
        "Cria um novo endereço para o cliente autenticado. "
        "Todos os campos são obrigatórios conforme o schema AddressCreateIn."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def create_my_address_router(request, payload: AddressCreateIn):
    """
    Cadastra um novo endereço para o cliente autenticado.
    """
    try:
        user: User = request.auth
        address = register_address_for_client(
            user_id=user.id,
            data=payload
        )
        return 201, address
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Atualização ──────────────────────────────────────────────────────────────

@router.patch(
    "/my-addresses/{address_id}",
    response={200: AddressOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Atualiza um endereço existente",
    description=(
        "Atualiza os dados de um endereço específico do cliente autenticado. "
        "Apenas os campos enviados no payload serão atualizados (PATCH)."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def update_my_address_router(request, address_id: uuid.UUID, payload: AddressUpdateIn):
    """
    Atualiza um endereço do cliente autenticado.
    """
    try:
        user: User = request.auth
        address = update_address_for_client(
            user_id=user.id,
            address_id=address_id,
            payload=payload
        )
        return 200, address
    except (UserNotFound, AddressNotFound) as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Ativação/Desativação ──────────────────────────────────────────────────────

@router.post(
    "/my-addresses/{address_id}/activate",
    response={200: AddressOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Ativa um endereço (check-up)",
    description=(
        "Ativa/check-up um endereço do cliente autenticado. "
        "O endereço precisa pertencer ao cliente para ser ativado."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def activate_my_address_router(request, address_id: uuid.UUID):
    """
    Ativa um endereço do cliente autenticado.
    """
    try:
        user: User = request.auth
        address = update_address_check_up(
            user_id=user.id,
            address_id=address_id
        )
        return 200, address
    except (UserNotFound, AddressNotFound) as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}


@router.post(
    "/my-addresses/{address_id}/deactivate",
    response={200: AddressOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Desativa um endereço (check-down)",
    description=(
        "Desativa/check-down um endereço do cliente autenticado. "
        "O endereço precisa pertencer ao cliente para ser desativado."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def deactivate_my_address_router(request, address_id: uuid.UUID):
    """
    Desativa um endereço do cliente autenticado.
    """
    try:
        user: User = request.auth
        address = update_address_check_down(
            user_id=user.id,
            address_id=address_id
        )
        return 200, address
    except (UserNotFound, AddressNotFound) as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}


# ── Definição de Preferencial ────────────────────────────────────────────────

@router.post(
    "/my-addresses/{address_id}/set-preferential",
    response={200: AddressOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Define um endereço como preferencial",
    description=(
        "Marca um endereço específico do cliente como preferencial. "
        "O endereço precisa pertencer ao cliente. "
        "Se outro endereço for preferencial, ele será desmarcado automaticamente."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def set_preferential_address_router(request, address_id: uuid.UUID):
    """
    Define um endereço como preferencial para o cliente autenticado.
    """
    try:
        user: User = request.auth
        
        # Verifica se o endereço pertence ao cliente
        if not validate_address_belongs_to_client(user_id=user.id, address_id=address_id):
            return 404, {"detail": "Endereço não encontrado ou não pertence ao cliente."}
        
        # Busca o endereço atual preferencial e desativa
        current_preferential = get_preferential_address_for_client(user_id=user.id)
        if current_preferential and current_preferential.address_id != address_id:
            # Desativa o preferencial atual
            update_address_check_down(
                user_id=user.id,
                address_id=current_preferential.address_id
            )
        
        # Ativa o novo endereço preferencial
        address = update_address_check_up(
            user_id=user.id,
            address_id=address_id
        )
        
        return 200, address
    except (UserNotFound, AddressNotFound) as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ── Verificação de existência ───────────────────────────────────────────────

@router.get(
    "/my-addresses/{address_id}/exists",
    response={200: dict, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Verifica se um endereço existe e pertence ao cliente",
    description=(
        "Verifica se um endereço específico existe e pertence ao cliente autenticado. "
        "Retorna { 'exists': true } se o endereço pertence ao cliente."
    ),
)
@ratelimit(key="user", rate="60/m", block=True)
def check_my_address_exists_router(request, address_id: uuid.UUID):
    """
    Verifica se o endereço existe e pertence ao cliente.
    """
    try:
        user: User = request.auth
        exists = validate_address_belongs_to_client(
            user_id=user.id,
            address_id=address_id
        )
        return 200, {"exists": exists}
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except ClientNotFoundError as e:
        return 403, {"detail": str(e)}