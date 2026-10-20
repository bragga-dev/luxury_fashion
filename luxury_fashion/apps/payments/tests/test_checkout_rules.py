"""Regras do checkout: frete cotado pro endereço do pedido, item ativo, preço atual e estoque intocado."""
from decimal import Decimal

import pytest

from luxury_fashion.apps.cart.models.cart_item_model import CartItem
from luxury_fashion.apps.cart.schemas.cart_item_schema import CartItemCreateIn
from luxury_fashion.apps.cart.services.cart_item_service import add_item_to_cart
from luxury_fashion.apps.core.exceptions import ShippingNotFound
from luxury_fashion.apps.core.exceptions.cart_exception import (
    CartPriceChanged,
    InsufficientStock,
    ProductUnavailable,
    ShippingOptionUnavailable,
)
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn
from luxury_fashion.apps.payments.services.order_service import create_order_from_cart

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _frete(variant_shipping, frenet_calls):
    """Embalagem cadastrada + Frenet mockada em todo checkout."""


def _checkout(user, address, code="04510"):
    return create_order_from_cart(
        user_id=user.user_id,
        data=OrderCreateIn(shipping_address_id=address.address_id, shipping_service_code=code),
    )


def test_checkout_grava_frete_no_pedido_com_preco_da_frenet(user, client_profile, address, cart, cart_item):
    result = _checkout(user, address)
    assert result.order_shipping_total == Decimal("21.50")
    assert result.total_geral == result.subtotal + Decimal("21.50")
    assert result.shipping_service_code == "04510"
    assert result.shipping_delivery_days == 6


def test_checkout_nao_mexe_no_carrinho_alem_de_esvaziar_nem_guarda_frete_nele(user, client_profile, address, cart, cart_item):
    _checkout(user, address)
    cart.refresh_from_db()
    assert cart.items.count() == 0
    assert cart.total_price == Decimal("0.00")
    assert not hasattr(cart, "total_shipping")  # frete não mora no carrinho


@pytest.mark.parametrize("code", ["999", "NAO-EXISTE"])
def test_checkout_recusa_servico_inexistente_ou_com_erro(user, client_profile, address, cart, cart_item, code):
    with pytest.raises(ShippingOptionUnavailable):
        _checkout(user, address, code=code)
    assert Order.objects.count() == 0


def test_checkout_recusa_variante_sem_dados_de_frete(user, client_profile, address, cart, cart_item, variant_shipping):
    variant_shipping.delete()
    with pytest.raises(ShippingNotFound):
        _checkout(user, address)


def test_checkout_nao_debita_estoque(user, client_profile, address, cart, cart_item, variant):
    estoque = variant.stock
    _checkout(user, address)
    variant.refresh_from_db()
    assert variant.stock == estoque


def test_checkout_recusa_quando_quantidade_passa_do_estoque(user, client_profile, address, cart, cart_item, variant):
    variant.stock = cart_item.quantity_item - 1
    variant.save()
    with pytest.raises(InsufficientStock):
        _checkout(user, address)


def test_checkout_recusa_variante_inativa(user, client_profile, address, cart, cart_item, variant):
    variant.is_active = False
    variant.save()
    with pytest.raises(ProductUnavailable):
        _checkout(user, address)


def test_checkout_recusa_produto_inativo(user, client_profile, address, cart, cart_item, product):
    product.is_active = False
    product.save()
    with pytest.raises(ProductUnavailable):
        _checkout(user, address)


def test_checkout_com_preco_alterado_recusa_e_persiste_o_preco_novo(user, client_profile, address, cart, cart_item, variant):
    variant.price = Decimal("120.00")
    variant.save()

    with pytest.raises(CartPriceChanged):
        _checkout(user, address)

    cart_item.refresh_from_db()
    cart.refresh_from_db()
    assert cart_item.unit_price_item == Decimal("120.00")
    assert cart.total_price == Decimal("240.00")


def test_nao_adiciona_variante_inativa_ao_carrinho(user, client_profile, cart, variant):
    variant.is_active = False
    variant.save()
    with pytest.raises(ProductUnavailable):
        add_item_to_cart(user.user_id, CartItemCreateIn(variant_id=variant.variant_id, quantity_item=1))
    assert CartItem.objects.count() == 0