"""
Cart endpoints — carrinho e itens do cliente autenticado.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router, Status

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.cart.schemas.cart_item_schema import CartItemCreateIn, CartItemUpdateIn
from luxury_fashion.apps.cart.schemas.cart_schema import CartOut
from luxury_fashion.apps.cart.schemas.cart_shipping_schema import CartShippingQuoteIn
from luxury_fashion.apps.cart.services.cart_item_service import (
    add_item_to_cart,
    remove_item_from_cart,
    update_cart_item_quantity,
)
from luxury_fashion.apps.cart.services.cart_service import clear_cart_for_client, get_cart_for_client
from luxury_fashion.apps.cart.services.cart_shipping_service import quote_shipping_for_cart
from luxury_fashion.apps.core.exceptions import EmptyCart, ShippingNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import (
    CartItemNotFound,
    CartNotFound,
    InsufficientStock,
    ProductUnavailable,
)
from luxury_fashion.apps.core.exceptions.shipping import FrenetAPIError
from luxury_fashion.apps.products.schemas.product_shipping_schema import FrenetShippingOptionOut
from luxury_fashion.apps.core.exceptions.products_exception import VariantNotFound
from luxury_fashion.apps.core.exceptions.user import UserNotFound
from luxury_fashion.apps.core.permissions.auth_classes import ClientOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut

router = Router()


# ── Carrinho ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response={200: CartOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Retorna o carrinho do cliente autenticado",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_my_cart_router(request):
    try:
        user: User = request.auth
        return Status(200, get_cart_for_client(user.user_id))
    except (CartNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})


@router.delete(
    "",
    response={200: CartOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Esvazia o carrinho do cliente autenticado",
)
@ratelimit(key="user", rate="20/h", block=True)
def clear_my_cart_router(request):
    try:
        user: User = request.auth
        return Status(200, clear_cart_for_client(user.user_id))
    except UserNotFound as e:
        return Status(404, {"detail": str(e)})


# ── Frete ─────────────────────────────────────────────────────────────────────

@router.post(
    "/shipping/quote",
    response={200: list[FrenetShippingOptionOut], 400: MessageOut, 404: MessageOut, 409: MessageOut, 502: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cota o frete do carrinho inteiro (todos os itens) para um CEP",
    description="Somente consulta — nada é gravado. O frete escolhido (`service_code`) é enviado no `POST /orders`, que recota e grava no pedido.",
)
@ratelimit(key="user", rate="20/m", block=True)
def quote_cart_shipping_router(request, payload: CartShippingQuoteIn):
    try:
        user: User = request.auth
        return Status(200, quote_shipping_for_cart(user.user_id, payload))
    except UserNotFound as e:
        return Status(404, {"detail": str(e)})
    except EmptyCart as e:
        return Status(400, {"detail": str(e)})
    except ShippingNotFound as e:
        return Status(409, {"detail": str(e)})
    except FrenetAPIError as e:
        return Status(502, {"detail": str(e)})


# ── Itens ─────────────────────────────────────────────────────────────────────

@router.post(
    "/items",
    response={201: CartOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Adiciona uma variante ao carrinho",
    description=(
        "Adiciona `quantity_item` unidades da variante ao carrinho. Se a "
        "variante já estiver no carrinho, soma na quantidade existente."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def add_cart_item_router(request, payload: CartItemCreateIn):
    try:
        user: User = request.auth
        return Status(201, add_item_to_cart(user.user_id, payload))
    except (VariantNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})
    except (InsufficientStock, ProductUnavailable) as e:
        return Status(409, {"detail": str(e)})
    except DjangoValidationError as e:
        return Status(400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)})


@router.patch(
    "/items/{cart_item_id}",
    response={200: CartOut, 404: MessageOut, 409: MessageOut, 400: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Atualiza a quantidade de um item do carrinho",
    description="Define a quantidade exata do item (não soma).",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_cart_item_router(request, cart_item_id: uuid.UUID, payload: CartItemUpdateIn):
    try:
        user: User = request.auth
        return Status(200, update_cart_item_quantity(user.user_id, cart_item_id, payload.quantity_item))
    except (CartItemNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})
    except (InsufficientStock, ProductUnavailable) as e:
        return Status(409, {"detail": str(e)})
    except DjangoValidationError as e:
        return Status(400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)})


@router.delete(
    "/items/{cart_item_id}",
    response={200: CartOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Remove um item do carrinho",
)
@ratelimit(key="user", rate="30/m", block=True)
def remove_cart_item_router(request, cart_item_id: uuid.UUID):
    try:
        user: User = request.auth
        return Status(200, remove_item_from_cart(user.user_id, cart_item_id))
    except (CartItemNotFound, UserNotFound) as e:
        return Status(404, {"detail": str(e)})