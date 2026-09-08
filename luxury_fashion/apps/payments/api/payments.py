"""
Payment endpoints — geração de cobrança na Asaas pra um pedido, consulta e
estorno. O webhook público fica em api/webhook.py (não passa por
ClientOnlyAuth — quem chama é a Asaas, não o cliente logado).
"""
import uuid

from ninja import Router
from django_ratelimit.decorators import ratelimit

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions import (
    AsaasAPIError,
    CpfOrCnpjRequired,
    OrderAlreadyPaid,
    OrderNotFound,
    OrderNotPayable,
    PaymentNotFound,
    PaymentNotRefundable,
)
from luxury_fashion.apps.core.permissions.auth_classes import ClientOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.schemas.payment_schema import PaymentCreateIn, PaymentOut, RefundIn
from luxury_fashion.apps.payments.services.payment_service import (
    create_payment_for_order,
    get_payment_for_client,
    list_payments_for_order,
    refund_payment,
)

router = Router()


@router.post(
    "/orders/{order_id}/payments",
    response={201: PaymentOut, 400: MessageOut, 404: MessageOut, 409: MessageOut, 502: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Gera uma cobrança na Asaas para o pedido",
)
@ratelimit(key="user", rate="10/m", block=True)
def create_payment_router(request, order_id: uuid.UUID, payload: PaymentCreateIn):
    try:
        user: User = request.auth
        return 201, create_payment_for_order(user.user_id, order_id, payload)
    except OrderNotFound as e:
        return 404, {"detail": str(e)}
    except (OrderNotPayable, OrderAlreadyPaid) as e:
        return 409, {"detail": str(e)}
    except CpfOrCnpjRequired as e:
        return 400, {"detail": str(e)}
    except AsaasAPIError as e:
        return 502, {"detail": e.message}


@router.get(
    "/orders/{order_id}/payments",
    response={200: list[PaymentOut], 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Lista as cobranças de um pedido",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_order_payments_router(request, order_id: uuid.UUID):
    try:
        user: User = request.auth
        return 200, list_payments_for_order(user.user_id, order_id)
    except OrderNotFound as e:
        return 404, {"detail": str(e)}


@router.get(
    "/payments/{payment_id}",
    response={200: PaymentOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Retorna uma cobrança do cliente autenticado",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_payment_router(request, payment_id: uuid.UUID):
    try:
        user: User = request.auth
        return 200, get_payment_for_client(user.user_id, payment_id)
    except PaymentNotFound as e:
        return 404, {"detail": str(e)}


@router.post(
    "/payments/{payment_id}/refund",
    response={200: PaymentOut, 404: MessageOut, 409: MessageOut, 502: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Solicita estorno de uma cobrança paga",
)
@ratelimit(key="user", rate="10/m", block=True)
def refund_payment_router(request, payment_id: uuid.UUID, payload: RefundIn):
    try:
        user: User = request.auth
        return 200, refund_payment(user.user_id, payment_id, payload.value, payload.description)
    except PaymentNotFound as e:
        return 404, {"detail": str(e)}
    except PaymentNotRefundable as e:
        return 409, {"detail": str(e)}
    except AsaasAPIError as e:
        return 502, {"detail": e.message}