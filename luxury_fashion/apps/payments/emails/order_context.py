"""
Montagem de contexto para os e-mails de pedido (resumo, itens, frete, endereço).
Os helpers de URL e de nome do cliente já existem em products/emails/product_context.py
e payments/emails/payment_context.py — aqui só o que é específico do pedido.
"""
from datetime import timedelta

from django.conf import settings

from luxury_fashion.apps.payments.emails.payment_context import build_frontend_url, client_orders_url, store_url
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.products.emails.product_context import resolve_client_display_name


def _address_lines(address) -> list[str]:
    line1 = f"{address.street}, {address.number}"
    if address.complement:
        line1 += f" — {address.complement}"
    return [line1, f"{address.neighborhood} — {address.city}/{address.state}", f"CEP {address.cep}"]


def build_order_block(order: Order) -> dict:
    items = [
        {
            "name": str(item.variant_id),
            "quantity": item.order_item_quantity,
            "unit_price": item.order_item_price,
            "subtotal": item.order_item_price * item.order_item_quantity,
        }
        for item in order.items.select_related("variant_id__product_id")
    ]
    return {
        "order_code": order.code,
        "order_items": items,
        "order_subtotal": order.subtotal,
        "order_shipping_total": order.order_shipping_total,
        "order_total": order.total_geral,
        "order_shipping_service": order.shipping_service_name,
        "order_delivery_days": order.shipping_delivery_days,
        "order_address_lines": _address_lines(order.shipping_address),
        "order_created_at": order.created_at,
        "order_tracking_code": order.shipping_tracking_code,
        "payment_deadline": order.created_at + timedelta(hours=settings.ORDER_PENDING_EXPIRATION_HOURS),
    }


def build_order_email_context(order: Order) -> dict:
    return {
        "client_name": resolve_client_display_name(order.user_id),
        **build_order_block(order),
        "client_orders_url": client_orders_url(),
        "store_url": store_url(),
    }


def forgot_password_url() -> str:
    return build_frontend_url("/esqueci-senha")