"""
Helpers privados de montagem de contexto para os e-mails de envio de produtos.

"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from django.conf import settings

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,
    get_client_full_name_display,
)

from luxury_fashion.apps.core.permissions.roles import is_client
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


_CLIENT_ORDERS_PATH = "/painel/meus-pedidos"
_STORE_PATH = "/"
_NEW_ORDER_PATH = "/comprar-mais"
_RATE_ORDER_PATH_TEMPLATE = "/painel/meus-agendamentos/{scheduling_id}"


def build_frontend_url(path: str) -> str:
    """Monta uma URL absoluta do frontend a partir de um path relativo."""
    return f"{settings.FRONTEND_URL}{path}"


def client_orders_url() -> str:
    """Link para a área 'Meus pedidos' do cliente."""
    return build_frontend_url(_CLIENT_ORDERS_PATH)


def store_url() -> str:
    """Link para a página da loja."""
    return build_frontend_url(_STORE_PATH)


def new_order_url() -> str:
    """Link para comprar outros produtos."""
    return build_frontend_url(_NEW_ORDER_PATH)


def rate_order_url(order_id: UUID) -> str:
    """Link para avaliar um pedido concluído."""
    return build_frontend_url(_RATE_ORDER_PATH_TEMPLATE.format(order_id=order_id))


def resolve_client_display_name(user: User) -> str:
    """
    Resolve o nome de exibição do cliente a partir do `user`.
    Usa o e-mail como fallback quando o perfil de Client ainda não existe
    (ex.: e-mail disparado antes do onboarding do perfil ser concluído).
    """
    client = get_client_by_user_id(user_id=user.user_id)
    if client is None:
        return user.email
    return get_client_full_name_display(client)



def resolve_actor_display_name(user: Optional[User]) -> str:
    if user is None:
        return "ÉLUXO MODAS"
    if is_client(user):
        return resolve_client_display_name(user)
    return "ÉLUXO MODAS"

def format_datetime_br(value: datetime) -> str:
    """Formata data/hora no padrão pt-BR usado em todos os e-mails: dd/mm/aaaa às HH:MM."""
    return value.strftime("%d/%m/%Y às %H:%M")


def build_product_block(variant: ProductVariant) -> dict:
    """Campos de produto + valores praticados no momento do agendamento."""
    return {
        "produtct_name": variant.product_id.name,
        "produtct_description": variant.description,
        "product_image": variant.product_id.images,
        "product_price": variant.price,
        "product_size": variant.size,
        "product_color": variant.color,
        "product_gender": variant.gender,
    }

def build_order_datetime_block(order: Order) -> dict:
    """Campos de data/horário do pedido, já formatados em pt-BR, e status atual."""
    return {
        "order_created_at": format_datetime_br(order.created_at),
        "order_canceled_at": format_datetime_br(order.canceled_at) if order.canceled_at else None,
        "order_completed_at": format_datetime_br(order.completed_at) if order.completed_at else None,
        "order_status": order.get_order_status_display(),
    }