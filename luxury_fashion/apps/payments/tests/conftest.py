"""
Fixtures compartilhadas dos testes do módulo de pagamentos.

Nenhum teste aqui fala com a Asaas de verdade — o AsaasClient é sempre
mockado (via monkeypatch ou unittest.mock). Banco é sqlite em memória
(ver luxury_fashion.config.settings.test).
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.cart.models.cart_item_model import CartItem
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.payments.models.asaas_customer_model import AsaasCustomer
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.products.models.product_category_model import ProductCategory
from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


@pytest.fixture(autouse=True)
def mocked_send_payment_request_task(monkeypatch):
    """
    Impede que `create_payment_for_order` dispare Celery de verdade.

    A task em si (montagem de e-mail, integração com Asaas customer) tem
    testes próprios; aqui só garantimos que os testes do service/API não
    dependam de um broker Celery real disponível.
    """
    from luxury_fashion.apps.payments.tasks.send_payment_request import send_payment_request

    fake_delay = MagicMock()
    monkeypatch.setattr(send_payment_request, "delay", fake_delay)
    return fake_delay


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="cliente@example.com",
        password="senha-super-segura-123",
        is_active=True,
        is_trusty=True,
    )


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(
        email="outro@example.com",
        password="senha-super-segura-123",
        is_active=True,
        is_trusty=True,
    )


@pytest.fixture
def client_profile(user) -> Client:
    client = Client(user_id=user, first_name="Maria", last_name="Silva")
    client.cpf = "39053344705"  # CPF válido (dígitos verificadores ok)
    client.save()
    return client


@pytest.fixture
def address(client_profile) -> AddressesClient:
    return AddressesClient.objects.create(
        client_id=client_profile,
        cep="45200-000",
        street="Rua das Flores",
        number="100",
        neighborhood="Centro",
        city="Jequié",
        state="BA",
    )


@pytest.fixture
def order(user, address) -> Order:
    return Order.objects.create(
        user_id=user,
        shipping_address=address,
        subtotal=Decimal("199.90"),
        order_shipping_total=Decimal("20.00"),
        total_geral=Decimal("219.90"),
    )


@pytest.fixture
def product_category(db) -> ProductCategory:
    return ProductCategory.objects.create(category_name="Vestidos")


@pytest.fixture
def product(product_category) -> Product:
    return Product.objects.create(product_category_id=product_category, product_name="Vestido Longo")


@pytest.fixture
def variant(product) -> ProductVariant:
    return ProductVariant.objects.create(
        product_id=product,
        size=Product.ProductSize.M,
        color=Product.ProductColor.BLACK,
        gender=Product.ProductGender.FEMININO,
        price=Decimal("199.90"),
        stock=5,
    )


@pytest.fixture
def other_variant(product) -> ProductVariant:
    return ProductVariant.objects.create(
        product_id=product,
        size=Product.ProductSize.G,
        color=Product.ProductColor.RED,
        gender=Product.ProductGender.FEMININO,
        price=Decimal("249.90"),
        stock=3,
    )


@pytest.fixture
def cart(user) -> Cart:
    return Cart.objects.create(user_id=user)


@pytest.fixture
def cart_item(cart, variant) -> CartItem:
    item = CartItem.objects.create(cart_id=cart, variant_id=variant, quantity_item=2)
    cart.update_totals()
    return item


@pytest.fixture
def asaas_customer(client_profile) -> AsaasCustomer:
    return AsaasCustomer.objects.create(
        client_id=client_profile,
        asaas_customer_id="cus_000000000001",
    )


@pytest.fixture
def pending_payment(order) -> Payment:
    return Payment.objects.create(
        order_id=order,
        billing_type=Payment.PaymentMode.PIX,
        value=order.total_geral,
        due_date=date.today() + timedelta(days=1),
        description=f"Pedido {order.code}",
        external_reference=str(order.order_id),
        asaas_payment_id="pay_000000000001",
        status=Payment.PaymentStatus.PENDING,
        synced_with_asaas=True,
    )