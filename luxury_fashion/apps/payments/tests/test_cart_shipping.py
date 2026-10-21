"""Cotação de frete do carrinho (somente leitura). A Frenet é mockada (ver conftest)."""
import pytest
from ninja_jwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def test_quote_devolve_so_opcoes_validas_e_cota_todos_os_itens(client, user, cart, cart_item, variant_shipping, frenet_calls):
    resp = client.post("/api/cart/shipping/quote", data={"recipient_cep": "45200-000"},
                       content_type="application/json", **auth_header(user))
    assert resp.status_code == 200, resp.content
    assert [o["service_code"] for o in resp.json()] == ["04510", "04014"]

    sent = frenet_calls[0]
    assert sent["recipient_cep"] == "45200000"
    assert sent["items"][0]["quantity"] == cart_item.quantity_item  # quantidade real do carrinho
    assert sent["invoice_value"] == cart_item.subtotal()


def test_quote_nao_grava_nada_no_carrinho(client, user, cart, cart_item, variant_shipping, frenet_calls):
    antes = cart.total_price
    client.post("/api/cart/shipping/quote", data={"recipient_cep": "45200000"},
                content_type="application/json", **auth_header(user))
    cart.refresh_from_db()
    assert cart.total_price == antes


def test_nao_existe_rota_para_gravar_frete_no_carrinho(client, user, cart, cart_item):
    resp = client.post("/api/cart/shipping", data={"recipient_cep": "45200000", "service_code": "04510"},
                       content_type="application/json", **auth_header(user))
    assert resp.status_code in (404, 405)


def test_variante_sem_dados_de_frete_da_409(client, user, cart, cart_item, frenet_calls):
    resp = client.post("/api/cart/shipping/quote", data={"recipient_cep": "45200000"},
                       content_type="application/json", **auth_header(user))
    assert resp.status_code == 409
    assert frenet_calls == []


def test_carrinho_vazio_da_400(client, user, cart, variant_shipping, frenet_calls):
    resp = client.post("/api/cart/shipping/quote", data={"recipient_cep": "45200000"},
                       content_type="application/json", **auth_header(user))
    assert resp.status_code == 400


def test_cep_invalido_da_422(client, user, cart, cart_item):
    resp = client.post("/api/cart/shipping/quote", data={"recipient_cep": "123"},
                       content_type="application/json", **auth_header(user))
    assert resp.status_code == 422