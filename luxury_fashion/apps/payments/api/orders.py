"""
Order endpoints — checkout do carrinho e consulta de pedidos do cliente
autenticado.
"""
import uuid

from ninja import Router
from django_ratelimit.decorators import ratelimit

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions import EmptyCart, OrderNotFound, OrderNotPayable, UserNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.permissions.auth_classes import ClientOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn, OrderOut
from luxury_fashion.apps.payments.services.order_service import (
    cancel_order,
    create_order_from_cart,
    get_order_for_client,
    list_orders_for_client,
)

router = Router()


@router.post(
    "",
    response={201: OrderOut, 400: MessageOut, 403: MessageOut, 404: MessageOut, 409: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Faz o checkout do carrinho e cria um pedido",
)
@ratelimit(key="user", rate="10/m", block=True)
def create_order_router(request, payload: OrderCreateIn):
    try:
        user: User = request.auth
        return 201, create_order_from_cart(user.user_id, payload)
    except (UserNotFound, OrderNotFound) as e:
        return 404, {"detail": str(e)}
    except PermissionDenied as e:
        return 403, {"detail": str(e)}
    except EmptyCart as e:
        return 400, {"detail": str(e)}
    except InsufficientStock as e:
        return 409, {"detail": str(e)}


@router.get(
    "",
    response={200: list[OrderOut]},
    auth=ClientOnlyAuth(),
    summary="Lista os pedidos do cliente autenticado",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_orders_router(request):
    user: User = request.auth
    return 200, list_orders_for_client(user.user_id)


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
        return 200, get_order_for_client(user.user_id, order_id)
    except OrderNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/{order_id}/cancel",
    response={200: OrderOut, 404: MessageOut, 409: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cancela um pedido pendente e devolve o estoque",
)
@ratelimit(key="user", rate="10/m", block=True)
def cancel_order_router(request, order_id: uuid.UUID):
    try:
        user: User = request.auth
        return 200, cancel_order(user.user_id, order_id)
    except OrderNotFound as e:
        return 404, {"detail": str(e)}
    except OrderNotPayable as e:
        return 409, {"detail": str(e)}