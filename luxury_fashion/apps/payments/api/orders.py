"""
Order endpoints — checkout do carrinho e consulta de pedidos do cliente
autenticado.
"""
import uuid
from datetime import date
from typing import Optional

from ninja import Router, Status
from django_ratelimit.decorators import ratelimit

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions import EmptyCart, OrderNotFound, OrderNotPayable, ShippingNotFound, UserNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import (
    CartPriceChanged,
    InsufficientStock,
    ProductUnavailable,
    ShippingOptionUnavailable,
)
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.exceptions.shipping import (
    FrenetAPIError,
    FrenetInsufficientBalanceError,
    FrenetPartnerTokenMissingError,
    OrderDeliveryNotAllowed,
    OrderLabelNotAllowed,
)
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth, ClientOnlyAuth, ClientCompleteProfileAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT
from luxury_fashion.apps.payments.schemas.order_admin_schema import OrderAdminListOut, OrderAdminOut, OrderSummaryOut
from luxury_fashion.apps.payments.schemas.order_schema import (
    OrderCancelIn,
    OrderCreateIn,
    OrderOut,
    ShippingStatusEnum,
    StatusOrderEnum,
)
from luxury_fashion.apps.payments.services.order_admin_service import (
    get_order_for_admin,
    get_orders_summary_for_admin,
    list_orders_for_admin,
)
from luxury_fashion.apps.payments.services.order_delivery_service import mark_order_as_delivered
from luxury_fashion.apps.payments.services.order_service import (
    cancel_order_by_client,
    create_order_from_cart,
    get_order_for_client,
    list_orders_for_client,
)
from luxury_fashion.apps.payments.services.order_shipping_service import generate_label_for_order

router = Router()


@router.post(
    "",
    response={201: OrderOut, 400: MessageOut, 403: MessageOut, 404: MessageOut, 409: MessageOut, 502: MessageOut},
    auth=ClientCompleteProfileAuth(),
    summary="Faz o checkout do carrinho e cria um pedido",
    description=(
        "Valida disponibilidade e preços (sem mexer no estoque — ele é debitado quando o pagamento "
        "é efetivado), recota o frete pro CEP do endereço de entrega com o `shipping_service_code` "
        "escolhido e grava preço, serviço e prazo no pedido."
    ),
)
@ratelimit(key="user", rate="10/m", block=True)
def create_order_router(request, payload: OrderCreateIn):
    try:
        user: User = request.auth
        return Status(201, create_order_from_cart(user.user_id, payload))
    except (UserNotFound, OrderNotFound) as e:
        return Status(404, {"detail": str(e)})
    except PermissionDenied as e:
        return Status(403, {"detail": str(e)})
    except EmptyCart as e:
        return Status(400, {"detail": str(e)})
    except (
        InsufficientStock,
        ProductUnavailable,
        CartPriceChanged,
        ShippingOptionUnavailable,
        ShippingNotFound,
    ) as e:
        return Status(409, {"detail": str(e)})
    except FrenetAPIError as e:
        return Status(502, {"detail": str(e)})


# ── Admin ────────────────────────────────────────────────────────────────────
# Rotas /admin/* ANTES das rotas com {order_id}, senão "admin" seria lido como id.

@router.get(
    "/admin/list",
    response={200: PageOut[OrderAdminListOut]},
    auth=AdminOnlyAuth(),
    summary="Lista pedidos de todos os clientes (admin — paginado, com filtros)",
    description=(
        "Filtros: `order_status`, `shipping_status`, `search` (código, e-mail ou nome do cliente), "
        "`date_from`/`date_to` (data de criação, YYYY-MM-DD)."
    ),
)
@ratelimit(key="user", rate="60/m", block=True)
def list_orders_admin_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    order_status: Optional[StatusOrderEnum] = None,
    shipping_status: Optional[ShippingStatusEnum] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    return Status(
        200,
        list_orders_for_admin(
            page=page,
            page_size=page_size,
            order_status=order_status.value if order_status else None,
            shipping_status=shipping_status.value if shipping_status else None,
            search=search,
            date_from=date_from,
            date_to=date_to,
        ),
    )


@router.get(
    "/admin/summary",
    response={200: OrderSummaryOut},
    auth=AdminOnlyAuth(),
    summary="Totais do dashboard de pedidos (admin)",
    description="Receita e ticket médio consideram só pedidos pagos e não reembolsados (COMPLETED).",
)
@ratelimit(key="user", rate="60/m", block=True)
def orders_summary_admin_router(request, date_from: Optional[date] = None, date_to: Optional[date] = None):
    return Status(200, get_orders_summary_for_admin(date_from=date_from, date_to=date_to))


@router.get(
    "/admin/{order_id}",
    response={200: OrderAdminOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Detalhe de qualquer pedido (admin)",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_order_admin_router(request, order_id: uuid.UUID):
    try:
        return Status(200, get_order_for_admin(order_id))
    except OrderNotFound as e:
        return Status(404, {"detail": str(e)})


# ── Cliente ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response={200: list[OrderOut]},
    auth=ClientOnlyAuth(),
    summary="Lista os pedidos do cliente autenticado",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_orders_router(request):
    user: User = request.auth
    return Status(200, list_orders_for_client(user.user_id))


@router.get(
    "/{order_id}",
    response={200: OrderOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Retorna um pedido do cliente autenticado",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_order_router(request, order_id: uuid.UUID):
    try:
        user: User = request.auth
        return Status(200, get_order_for_client(user.user_id, order_id))
    except OrderNotFound as e:
        return Status(404, {"detail": str(e)})


@router.post(
    "/{order_id}/cancel",
    response={200: OrderOut, 404: MessageOut, 409: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cancela um pedido pendente e devolve o estoque",
)
@ratelimit(key="user", rate="10/m", block=True)
def cancel_order_router(request, order_id: uuid.UUID, payload: OrderCancelIn = None):
    try:
        user: User = request.auth
        reason = payload.reason if payload else None
        return Status(200, cancel_order_by_client(user.user_id, order_id, reason=reason))
    except OrderNotFound as e:
        return Status(404, {"detail": str(e)})
    except OrderNotPayable as e:
        return Status(409, {"detail": str(e)})


@router.post(
    "/{order_id}/generate-label",
    response={200: dict, 400: MessageOut, 404: MessageOut, 502: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Gera (e paga com o saldo da carteira) a etiqueta de envio na Frenet — uso administrativo",
)
def generate_label(request, order_id: uuid.UUID):
    try:
        order = generate_label_for_order(order_id)
    except Order.DoesNotExist:
        return Status(404, {"detail": "Pedido não encontrado."})
    except (OrderLabelNotAllowed, FrenetPartnerTokenMissingError, FrenetInsufficientBalanceError) as e:
        return Status(400, {"detail": str(e)})
    except FrenetAPIError as e:
        return Status(502, {"detail": str(e)})

    return Status(
        200,
        {
            "success": True,
            "frenet_shipment_id": order.frenet_order_id,
            "tracking_code": order.shipping_tracking_code,
            "label_url": order.shipping_label_url,
        },
    )


@router.post(
    "/{order_id}/mark-delivered",
    response={200: OrderAdminOut, 404: MessageOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Marca o pedido como entregue — uso administrativo (fallback do webhook da Frenet)",
    description="Idempotente. Exige pedido pago e etiqueta já gerada. Notifica o cliente.",
)
@ratelimit(key="user", rate="30/m", block=True)
def mark_order_delivered_router(request, order_id: uuid.UUID):
    try:
        mark_order_as_delivered(order_id)
        return Status(200, get_order_for_admin(order_id))
    except OrderNotFound as e:
        return Status(404, {"detail": str(e)})
    except OrderDeliveryNotAllowed as e:
        return Status(409, {"detail": str(e)})