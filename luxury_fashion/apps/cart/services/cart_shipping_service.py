"""
Cart Shipping Service — COTAÇÃO do frete do carrinho (somente leitura).

Nada é gravado no carrinho: a cotação serve pro cliente comparar opções. O frete
escolhido só vira dado no PEDIDO (ver order_service), onde o backend recota
usando o CEP do endereço de entrega e grava o preço retornado pela Frenet.
"""
import uuid
from decimal import Decimal
from typing import List

from luxury_fashion.apps.cart.schemas.cart_shipping_schema import CartShippingQuoteIn
from luxury_fashion.apps.cart.selectors.cart_item_selector import get_items_by_cart
from luxury_fashion.apps.cart.services.cart_service import get_or_create_cart_for_user
from luxury_fashion.apps.core.exceptions import EmptyCart, ShippingNotFound
from luxury_fashion.apps.products.integrations.frenet_client import FrenetClient
from luxury_fashion.apps.products.schemas.product_shipping_schema import FrenetShippingOptionOut
from luxury_fashion.apps.products.selectors.product_shipping_selector import get_shipping_by_variant
from luxury_fashion.apps.products.services.frenet_service import parse_quote_response


def quote_cart_items(cart_items: list, recipient_cep: str) -> List[FrenetShippingOptionOut]:
    """Cota TODOS os itens do carrinho numa remessa só (quantidades reais)."""
    if not cart_items:
        raise EmptyCart()

    shipping_items = []
    invoice_value = Decimal("0.00")
    origin_cep = None
    for item in cart_items:
        shipping = get_shipping_by_variant(item.variant_id_id)
        if shipping is None:
            raise ShippingNotFound(f"A variante {item.variant_id} não tem dados de frete (peso/dimensões) cadastrados.")
        origin_cep = origin_cep or shipping.origin_zip_code
        shipping_items.append({
            "weight": shipping.weight,
            "length": shipping.length,
            "height": shipping.height,
            "width": shipping.width,
            "quantity": item.quantity_item,
        })
        invoice_value += item.subtotal()

    response = FrenetClient().calculate_shipping_for_items(
        seller_cep=origin_cep,
        recipient_cep=recipient_cep,
        items=shipping_items,
        invoice_value=invoice_value,
    )
    return parse_quote_response(response)


def valid_options(options: List[FrenetShippingOptionOut]) -> List[FrenetShippingOptionOut]:
    return [o for o in options if not o.error and o.service_code]


def quote_shipping_for_cart(user_id: uuid.UUID, data: CartShippingQuoteIn) -> List[FrenetShippingOptionOut]:
    cart = get_or_create_cart_for_user(user_id=user_id)
    cart_items = list(get_items_by_cart(cart_id=cart.cart_id))
    return valid_options(quote_cart_items(cart_items, data.recipient_cep))