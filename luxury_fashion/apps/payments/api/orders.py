"""
Order endpoints — checkout do carrinho e consulta de pedidos do cliente
autenticado.
"""
import uuid

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
    OrderLabelNotAllowed,
)
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth, ClientOnlyAuth, ClientCompleteProfileAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.schemas.order_schema import OrderCancelIn, OrderCreateIn, OrderOut
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