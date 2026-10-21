"""
Order Service — orquestra o checkout e o ciclo do pedido.

Regras importantes:
- O checkout NÃO mexe no estoque: ele só valida disponibilidade. O estoque é
  debitado quando o pagamento é efetivado (`confirm_order_payment`).
- O frete vem do PEDIDO: o cliente envia só o `shipping_service_code`; o backend recota
  na Frenet usando o CEP do endereço de entrega e grava preço, nome e prazo no pedido.
"""
import re
import uuid

from django.db import transaction

from luxury_fashion.apps.accounts.selectors.address_selector import get_address_by_id
from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.accounts.selectors.user_selector import get_user_by_id
from luxury_fashion.apps.cart.repositories.cart_item_repository import clear_cart
from luxury_fashion.apps.cart.selectors.cart_item_selector import get_items_by_cart
from luxury_fashion.apps.cart.selectors.cart_selector import get_cart_by_user_id
from luxury_fashion.apps.cart.services.cart_service import refresh_cart_prices
from luxury_fashion.apps.cart.services.cart_shipping_service import quote_cart_items, valid_options
from luxury_fashion.apps.core.exceptions import EmptyCart, OrderNotFound, OrderNotPayable, UserNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import (
    CartPriceChanged,
    InsufficientStock,
    ProductUnavailable,
    ShippingOptionUnavailable,
)
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.schemas.deafult_schema import PageOut
from luxury_fashion.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset
from luxury_fashion.apps.notifications.services.notification_service import (
    notify_admins_new_order_paid,
    notify_order_cancelled_no_stock,
    notify_order_expired,
    notify_order_paid,
)
from luxury_fashion.apps.payments.integrations.asaas_client import AsaasClient
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.repositories.order_repository import (
    bulk_create_order_items,
    canceled_order,
    completed_order,
    refunded_order,
    create_order,
)
from luxury_fashion.apps.payments.repositories.payment_repository import update_payment
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn, OrderOut
from luxury_fashion.apps.payments.selectors.order_selector import (
    get_order_by_id_and_user,
    get_orders_by_user,
)
from luxury_fashion.apps.payments.selectors.payment_selector import get_payments_by_order
from luxury_fashion.apps.payments.tasks.order_notifications import (
    queue_email,
    send_order_cancelled_email,
    send_order_received_email,
    send_payment_confirmed_email,
)
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant
from luxury_fashion.apps.products.repositories.product_variant_repository import adjust_variant_stock


def _validate_shipping_address(user_id: uuid.UUID, shipping_address_id: uuid.UUID):
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise UserNotFound()

    address = get_address_by_id(address_id=shipping_address_id)
    if address is None or address.client_id_id != client.client_id:
        raise PermissionDenied("Endereço não pertence ao cliente autenticado.")
    if address.is_archived:
        raise PermissionDenied("Este endereço não está mais disponível. Selecione outro endereço de entrega.")
    return address


def _load_variants(cart_items: list) -> dict:
    variant_ids = {item.variant_id_id for item in cart_items}
    return {
        v.variant_id: v
        for v in ProductVariant.objects.select_related("product_id").filter(variant_id__in=variant_ids)
    }


def _validate_items(cart_items: list, variants: dict) -> None:
    """Item ativo, com estoque suficiente e com o preço atual. NÃO reserva nem debita estoque."""
    for item in cart_items:
        variant = variants[item.variant_id_id]
        if not variant.is_active or not variant.product_id.is_active:
            raise ProductUnavailable(f"{variant} não está mais disponível. Remova do carrinho para continuar.")
        if item.quantity_item > variant.stock:
            raise InsufficientStock(f"Estoque insuficiente para {variant}.")
        if item.unit_price_item != variant.price:
            raise CartPriceChanged(f"O preço de {variant} mudou. Revise o carrinho antes de finalizar.")


def _fingerprint(cart_items: list) -> list:
    return sorted((str(i.variant_id_id), i.quantity_item) for i in cart_items)


def create_order_from_cart(user_id: uuid.UUID, data: OrderCreateIn) -> OrderOut:
    # 1) Preços: ressincroniza FORA da transação — se algum mudou a atualização precisa
    #    persistir mesmo com o checkout recusado (senão o cliente veria o mesmo erro pra sempre).
    if refresh_cart_prices(user_id=user_id):
        raise CartPriceChanged()

    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    shipping_address = _validate_shipping_address(user_id=user_id, shipping_address_id=data.shipping_address_id)

    cart = get_cart_by_user_id(user_id=user_id)
    cart_items = list(get_items_by_cart(cart_id=cart.cart_id)) if cart else []
    if not cart_items:
        raise EmptyCart()
    _validate_items(cart_items, _load_variants(cart_items))

    # 2) Frete: cotação na Frenet (chamada HTTP) também FORA da transação, pra não segurar
    #    conexão/locks do banco esperando API externa. O CEP é o do endereço de entrega.
    options = valid_options(quote_cart_items(cart_items, re.sub(r"\D", "", shipping_address.cep)))
    shipping_option = next((o for o in options if o.service_code == data.shipping_service_code), None)
    if shipping_option is None:
        raise ShippingOptionUnavailable()

    return _create_order_atomic(
        user=user,
        shipping_address=shipping_address,
        shipping_option=shipping_option,
        quoted_fingerprint=_fingerprint(cart_items),
    )


@transaction.atomic
def _create_order_atomic(user, shipping_address, shipping_option, quoted_fingerprint) -> OrderOut:
    cart = get_cart_by_user_id(user_id=user.user_id)
    cart_items = list(get_items_by_cart(cart_id=cart.cart_id)) if cart else []
    if not cart_items:
        raise EmptyCart()

    # O carrinho mudou entre a cotação e a gravação? Então o frete cotado não vale mais.
    if _fingerprint(cart_items) != quoted_fingerprint:
        raise CartPriceChanged("O carrinho foi alterado durante o checkout. Tente novamente.")
    _validate_items(cart_items, _load_variants(cart_items))

    shipping_total = shipping_option.price
    order = create_order(
        user=user,
        shipping_address=shipping_address,
        subtotal=cart.total_price,
        order_shipping_total=shipping_total,
        total_geral=cart.total_price + shipping_total,
        shipping_service_code=shipping_option.service_code,
        shipping_service_name=f"{shipping_option.carrier} - {shipping_option.service}".strip(" -"),
        shipping_delivery_days=shipping_option.delivery_time_days,
    )

    bulk_create_order_items(
        order=order,
        items=[
            {
                "variant": item.variant_id,
                "quantity": item.quantity_item,
                "unit_price": item.unit_price_item,
            }
            for item in cart_items
        ],
    )

    clear_cart(cart=cart)
    queue_email(send_order_received_email, order.order_id)

    return _order_out_for(user_id=user.user_id, order_id=order.order_id)


def _order_out_for(user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    return OrderOut.from_orm(order)


def get_order_for_client(user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()
    return OrderOut.from_orm(order)


def list_orders_for_client(user_id: uuid.UUID) -> list[OrderOut]:
    orders = get_orders_by_user(user_id=user_id)
    return [OrderOut.from_orm(order) for order in orders]


def page_orders_for_client(user_id: uuid.UUID, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT) -> PageOut[OrderOut]:
    """Pedidos do cliente, mais recentes primeiro, paginados."""
    return paginate_queryset(get_orders_by_user(user_id=user_id), page, page_size, OrderOut.from_orm)


def _lock_order(order_id: uuid.UUID) -> Order | None:
    """Trava a linha do pedido (evita corrida com o webhook de pagamento)."""
    return Order.objects.select_for_update().filter(order_id=order_id).first()


@transaction.atomic
def confirm_order_payment(order_id: uuid.UUID) -> bool:
    """
    Pagamento efetivado → ESTE é o momento em que o estoque é debitado.

    Devolve True se o pedido ficou (ou já estava) COMPLETED. Devolve False quando
    o pagamento não pode ser aceito e o caller deve estornar:
      - o pedido não pode mais ser concluído (cancelado/expirado/falho), ou
      - faltou estoque (outro cliente pagou antes pela última unidade): o pedido é
        cancelado aqui mesmo, sem debitar nada.
    Idempotente: evento duplicado do webhook não debita duas vezes.
    """
    order = _lock_order(order_id)
    if order is None:
        return False
    if order.order_status == Order.StatusOrder.COMPLETED:
        return True
    if not order.can_transition_to(Order.StatusOrder.COMPLETED):
        return False

    items = list(order.items.all())
    variant_ids = sorted({item.variant_id_id for item in items})  # ordenado: evita deadlock
    locked_variants = {
        v.variant_id: v
        for v in ProductVariant.objects.select_for_update().filter(variant_id__in=variant_ids)
    }

    if any(item.order_item_quantity > locked_variants[item.variant_id_id].stock for item in items):
        canceled_order(order=order, reason="Sem estoque no momento da confirmação do pagamento.")
        notify_order_cancelled_no_stock(order.order_id)
        queue_email(send_order_cancelled_email, order.order_id, "no_stock")
        return False

    for item in items:
        adjust_variant_stock(variant=locked_variants[item.variant_id_id], delta=-item.order_item_quantity)
    completed_order(order=order)
    notify_order_paid(order.order_id)
    notify_admins_new_order_paid(order.order_id)
    queue_email(send_payment_confirmed_email, order.order_id)
    return True


@transaction.atomic
def refund_order(order_id: uuid.UUID) -> bool:
    """
    Pagamento estornado → pedido COMPLETED vira REFUNDED.

    Estoque: o pagamento debitou, então o estorno devolve — MAS só se a mercadoria ainda não saiu
    (sem etiqueta e envio pendente). Depois de etiquetado/enviado o produto está fora do estoque
    físico; a reposição passa a ser manual (ajuste de estoque pelo admin quando a devolução chegar).

    Idempotente: devolve False se o pedido não pode mais ir pra REFUNDED (já estornado, etc.).
    """
    order = _lock_order(order_id)
    if order is None or not order.can_transition_to(Order.StatusOrder.REFUNDED):
        return False

    refunded_order(order=order)

    goods_still_here = not order.frenet_order_id and order.shipping_status == Order.ShippingStatus.PENDING
    if goods_still_here:
        items = list(order.items.all())
        variant_ids = sorted({item.variant_id_id for item in items})  # ordenado: evita deadlock
        locked_variants = {
            v.variant_id: v
            for v in ProductVariant.objects.select_for_update().filter(variant_id__in=variant_ids)
        }
        for item in items:
            adjust_variant_stock(variant=locked_variants[item.variant_id_id], delta=item.order_item_quantity)
    return True


@transaction.atomic
def cancel_order_by_client(user_id: uuid.UUID, order_id: uuid.UUID, reason: str | None = None) -> OrderOut:
    order = get_order_by_id_and_user(order_id=order_id, user_id=user_id)
    if order is None:
        raise OrderNotFound()

    locked = _lock_order(order.order_id)
    if locked is None or locked.order_status != Order.StatusOrder.PENDING:
        raise OrderNotPayable("Só é possível cancelar pedidos com pagamento pendente.")

    # PENDING nunca debitou estoque, então não há o que devolver.
    canceled_order(order=locked, reason=reason)
    # (sem notificação in-app: o cliente é o autor da ação — mas recebe o e-mail de confirmação)
    queue_email(send_order_cancelled_email, locked.order_id, "client", reason)
    return _order_out_for(user_id=user_id, order_id=order_id)


@transaction.atomic
def expire_pending_order(order_id: uuid.UUID) -> bool:
    """
    Cancela um pedido que ficou PENDING sem pagamento (chamado pela task periódica).
    Antes de cancelar, anula na Asaas as cobranças ainda abertas, pra ninguém pagar um
    pedido já cancelado; se a Asaas recusar (ex.: acabou de ser paga), levanta
    AsaasAPIError e a transação inteira é revertida — o webhook de pagamento resolve.
    Não mexe em estoque: pedido pendente nunca debitou.

    Devolve True se expirou, False se o pedido já não estava PENDING.
    """
    order = _lock_order(order_id)
    if order is None or order.order_status != Order.StatusOrder.PENDING:
        return False

    open_payments = [
        p for p in get_payments_by_order(order.order_id)
        if p.status == Payment.PaymentStatus.PENDING
    ]
    for payment in open_payments:
        if payment.asaas_payment_id:
            AsaasClient().cancel_payment(payment.asaas_payment_id)
        update_payment(payment, status=Payment.PaymentStatus.CANCELLED)

    canceled_order(order=order, reason="Pedido expirado por falta de pagamento.")
    notify_order_expired(order.order_id)
    queue_email(send_order_cancelled_email, order.order_id, "expired")
    return True