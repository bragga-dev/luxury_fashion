"""
Testes de integração dos endpoints de Order — sobem a API Ninja de
verdade (roteamento, auth, exception handlers) via Django test client.
"""
from decimal import Decimal

import pytest
from ninja_jwt.tokens import RefreshToken

from luxury_fashion.apps.payments.models.order_model import Order

pytestmark = pytest.mark.django_db


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class TestCreateOrderEndpoint:
    def test_checkout_creates_order_and_returns_201(self, client, user, client_profile, address, cart, cart_item):
        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": str(address.address_id)},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["order_status"] == "PENDING"
        assert len(body["items"]) == 1

    def test_requires_authentication(self, client, address):
        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": str(address.address_id)},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_requires_complete_profile(self, client, user):
        """Cliente sem CPF/endereço não passa no ClientCompleteProfileAuth (403)."""
        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": "00000000-0000-0000-0000-000000000000"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 403

    def test_returns_403_when_address_belongs_to_another_client(self, client, user, client_profile, address, other_user):
        from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
        from luxury_fashion.apps.accounts.models.client_model import Client

        other_client = Client(user_id=other_user, first_name="Outro", last_name="Cliente")
        other_client.cpf = "98765432100"
        other_client.save()
        foreign_address = AddressesClient.objects.create(
            client_id=other_client,
            cep="45200-000",
            street="Rua Alheia",
            number="1",
            neighborhood="Centro",
            city="Jequié",
            state="BA",
        )

        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": str(foreign_address.address_id)},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 403

    def test_returns_400_when_cart_is_empty(self, client, user, client_profile, address):
        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": str(address.address_id)},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 400

    def test_returns_409_when_stock_is_insufficient(self, client, user, client_profile, address, cart, variant):
        from luxury_fashion.apps.cart.models.cart_item_model import CartItem

        CartItem.objects.create(cart_id=cart, variant_id=variant, quantity_item=variant.stock + 1)

        resp = client.post(
            "/api/orders/",
            data={"shipping_address_id": str(address.address_id)},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 409


class TestListOrdersEndpoint:
    def test_lists_only_orders_of_authenticated_user(self, client, user, client_profile, address, other_user):
        Order.objects.create(user_id=user, shipping_address=address, total_geral=Decimal("10.00"))
        Order.objects.create(user_id=other_user, shipping_address=address, total_geral=Decimal("20.00"))

        resp = client.get("/api/orders/", **auth_header(user))

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_requires_authentication(self, client):
        resp = client.get("/api/orders/")
        assert resp.status_code == 401


class TestGetOrderEndpoint:
    def test_returns_order_of_authenticated_user(self, client, user, order):
        resp = client.get(f"/api/orders/{order.order_id}", **auth_header(user))
        assert resp.status_code == 200
        assert resp.json()["order_id"] == str(order.order_id)

    def test_returns_404_for_order_of_another_user(self, client, other_user, order):
        resp = client.get(f"/api/orders/{order.order_id}", **auth_header(other_user))
        assert resp.status_code == 404

    def test_returns_404_when_order_does_not_exist(self, client, user):
        resp = client.get(
            "/api/orders/00000000-0000-0000-0000-000000000000", **auth_header(user)
        )
        assert resp.status_code == 404


class TestCancelOrderEndpoint:
    def test_cancels_pending_order(self, client, user, order):
        resp = client.post(
            f"/api/orders/{order.order_id}/cancel",
            data={"reason": "Não preciso mais"},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 200
        assert resp.json()["order_status"] == "CANCELLED"

    def test_cancels_without_reason(self, client, user, order):
        resp = client.post(
            f"/api/orders/{order.order_id}/cancel",
            data={},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 200

    def test_returns_404_for_order_of_another_user(self, client, other_user, order):
        resp = client.post(
            f"/api/orders/{order.order_id}/cancel",
            data={},
            content_type="application/json",
            **auth_header(other_user),
        )
        assert resp.status_code == 404

    def test_returns_409_when_order_is_not_pending(self, client, user, order):
        order.complete()
        resp = client.post(
            f"/api/orders/{order.order_id}/cancel",
            data={},
            content_type="application/json",
            **auth_header(user),
        )
        assert resp.status_code == 409