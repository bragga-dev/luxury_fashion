"""
Regressão das correções da revisão pré-front: PII em reviews públicas, pagamento preso, endereço/itens
imutáveis, filtro de variante, nota média, exclusão protegida, estorno com reposição de estoque e
estoque do admin.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from ninja_jwt.tokens import RefreshToken

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.schemas.address_schema import AddressUpdateIn
from luxury_fashion.apps.accounts.services.address_service import (
    delete_address_for_client,
    update_address_for_client,
)
from luxury_fashion.apps.core.exceptions import CpfOrCnpjRequired
from luxury_fashion.apps.core.exceptions.products_exception import ProductInUse, VariantInUse
from luxury_fashion.apps.core.exceptions.service_exception import OrderItemNotReviewable
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.schemas.payment_schema import PaymentBillingTypeEnum, PaymentCreateIn
from luxury_fashion.apps.payments.services import order_service, payment_service
from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant
from luxury_fashion.apps.products.selectors.product_selector import filter_products
from luxury_fashion.apps.products.services.product_service import delete_product_for_admin
from luxury_fashion.apps.products.services.product_variant_service import (
    adjust_variant_stock_for_admin,
    delete_variant_for_admin,
    set_variant_stock_for_admin,
)
from luxury_fashion.apps.reviews.models.reviews_model import Reviews
from luxury_fashion.apps.reviews.schemas.reviews_schema import ReviewsCreateIn, ReviewsEnum
from luxury_fashion.apps.reviews.services.reviews_service import create_review_for_client


@pytest.fixture(autouse=True)
def _cep_sem_rede(monkeypatch):
    """validate_cep consulta a API de CEP de verdade no full_clean — aqui sempre responde OK."""
    from luxury_fashion.apps.core.validators import validate_cep as mod

    monkeypatch.setattr(mod.brazilcep, "get_address_from_cep", lambda cep: {"cep": cep})


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def paid_item(order, variant):
    """Pedido pago (COMPLETED) com um item, ainda sem envio."""
    Order.objects.filter(pk=order.pk).update(order_status=Order.StatusOrder.COMPLETED)
    order.refresh_from_db()
    return OrderItem.objects.create(
        order_id=order, variant_id=variant, order_item_quantity=2, order_item_price=variant.price,
        product_name=variant.product_id.product_name, variant_size=variant.size, variant_color=variant.color,
    )


# ── 1. Reviews públicas não vazam dados pessoais ──────────────────────────────

def test_reviews_publicas_nao_expoem_email_nem_ids_do_usuario(client, user, client_profile, paid_item, variant):
    Reviews.objects.create(order_item_id=paid_item, user_id=user, reviews=5, comment="Lindo", is_authorized=True)

    resp = client.get(f"/api/reviews/products/{variant.product_id.product_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    review = body["items"][0]
    assert review["author_name"] == "Maria S."
    assert review["comment"] == "Lindo"
    raw = resp.content.decode()
    assert user.email not in raw
    assert str(user.user_id) not in raw


def test_review_de_item_publica_sem_pii(client, user, client_profile, paid_item):
    Reviews.objects.create(order_item_id=paid_item, user_id=user, reviews=4, is_authorized=True)
    resp = client.get(f"/api/reviews/order-items/{paid_item.order_item_id}")
    assert resp.status_code == 200
    assert user.email not in resp.content.decode()


# ── 7. Só avalia depois de entregue ───────────────────────────────────────────

def test_nao_avalia_pedido_pago_mas_nao_entregue(user, client_profile, paid_item):
    with pytest.raises(OrderItemNotReviewable):
        create_review_for_client(user.user_id, ReviewsCreateIn(order_item_id=paid_item.order_item_id, reviews=ReviewsEnum.FIVE_STARS))


def test_avalia_pedido_entregue(user, client_profile, paid_item, order):
    Order.objects.filter(pk=order.pk).update(shipping_status=Order.ShippingStatus.DELIVERED)
    out = create_review_for_client(user.user_id, ReviewsCreateIn(order_item_id=paid_item.order_item_id, reviews=ReviewsEnum.FIVE_STARS))
    assert out.reviews == 5


# ── 2. Falha antes de criar a cobrança não deixa o pedido preso ───────────────

def test_falha_no_customer_cancela_payment_local_e_permite_nova_tentativa(
    monkeypatch, user, client_profile, order
):
    def boom(*a, **k):
        raise CpfOrCnpjRequired()

    monkeypatch.setattr(payment_service, "_get_or_create_asaas_customer", boom)
    monkeypatch.setattr(payment_service, "AsaasClient", MagicMock())
    payload = PaymentCreateIn(billing_type=PaymentBillingTypeEnum.PIX)

    with pytest.raises(CpfOrCnpjRequired):
        payment_service.create_payment_for_order(user.user_id, order.order_id, payload)

    payment = Payment.objects.get(order_id=order)
    assert payment.status == Payment.PaymentStatus.CANCELLED

    # segunda tentativa não pode bater em "pedido já pago/pagamento em aberto"
    with pytest.raises(CpfOrCnpjRequired):
        payment_service.create_payment_for_order(user.user_id, order.order_id, payload)


# ── 4. Endereço/itens do pedido não mudam ─────────────────────────────────────

def test_editar_endereco_usado_em_pedido_cria_novo_e_preserva_o_do_pedido(user, client_profile, address, order):
    out = update_address_for_client(user.user_id, address.address_id, AddressUpdateIn(street="Rua Nova"))

    assert out.address_id != address.address_id
    assert out.street == "Rua Nova"
    order.refresh_from_db()
    assert order.shipping_address.street == "Rua das Flores"  # destino do pedido intacto
    address.refresh_from_db()
    assert address.is_archived is True
    assert AddressesClient.objects.get(address_id=out.address_id).is_preferential is True


def test_editar_endereco_sem_pedido_edita_no_lugar(user, client_profile, address):
    out = update_address_for_client(user.user_id, address.address_id, AddressUpdateIn(street="Rua Nova"))
    assert out.address_id == address.address_id
    assert AddressesClient.objects.count() == 1


def test_excluir_endereco_usado_em_pedido_arquiva_em_vez_de_dar_500(user, client_profile, address, order):
    delete_address_for_client(user.user_id, address.address_id)
    address.refresh_from_db()
    assert address.is_archived is True
    order.refresh_from_db()  # pedido continua apontando pro endereço
    assert order.shipping_address_id == address.address_id


def test_endereco_arquivado_nao_aparece_na_lista_nem_serve_pra_novo_pedido(client, user, client_profile, address, order):
    delete_address_for_client(user.user_id, address.address_id)
    resp = client.get("/api/address/my-addresses", **auth_header(user))
    assert resp.status_code == 200
    assert "Rua das Flores" not in resp.content.decode()


def test_item_do_pedido_guarda_nome_tamanho_e_cor_da_compra(user, client_profile, address, cart, cart_item, variant, variant_shipping, frenet_calls):
    from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn

    created = order_service.create_order_from_cart(
        user_id=user.user_id,
        data=OrderCreateIn(shipping_address_id=address.address_id, shipping_service_code="04510"),
    )
    variant.product_id.product_name = "Outro Nome"
    variant.product_id.save()

    item = OrderItem.objects.get(order_id=created.order_id)
    assert item.product_name == "Vestido Longo"
    assert item.variant_size == variant.size
    assert item.variant_color == variant.color


# ── 5. Filtro size+color exige a MESMA variante ───────────────────────────────

def test_filtro_tamanho_e_cor_exige_a_mesma_variante(product, variant, other_variant):
    # variant = M/preto, other_variant = G/vermelho → "M + vermelho" não existe em nenhuma variante
    assert filter_products(size="M", color="red").count() == 0
    assert filter_products(size="M", color="black").count() == 1
    assert filter_products(size="G", color="red").count() == 1


def test_filtro_de_preco_e_ordenacao(product_category, variant):
    barato = Product.objects.create(product_category_id=product_category, product_name="Blusa", gender="feminino")
    ProductVariant.objects.create(product_id=barato, sku="B-1", size="P", color="white", price=Decimal("50.00"), stock=1)

    nomes_asc = [p.product_name for p in filter_products(sort="price_asc")]
    nomes_desc = [p.product_name for p in filter_products(sort="price_desc")]
    assert nomes_asc == ["Blusa", "Vestido Longo"]
    assert nomes_desc == ["Vestido Longo", "Blusa"]
    assert [p.product_name for p in filter_products(max_price=Decimal("100"))] == ["Blusa"]


# ── 6. Nota média na vitrine ─────────────────────────────────────────────────

def test_vitrine_e_detalhe_trazem_nota_media_so_de_avaliacoes_autorizadas(client, user, client_profile, paid_item, variant, order):
    Reviews.objects.create(order_item_id=paid_item, user_id=user, reviews=4, is_authorized=True)
    outro = OrderItem.objects.create(order_id=order, variant_id=variant, order_item_quantity=1, order_item_price=variant.price)
    Reviews.objects.create(order_item_id=outro, user_id=user, reviews=1, is_authorized=False)  # pendente: não conta

    lista = client.get("/api/products/").json()["items"][0]
    assert lista["total_reviews"] == 1
    assert Decimal(str(lista["average_rating"])) == Decimal("4.0")

    detalhe = client.get(f"/api/products/{variant.product_id.product_id}").json()
    assert detalhe["total_reviews"] == 1


def test_produto_sem_avaliacoes_tem_nota_zero(client, product, variant):
    item = client.get("/api/products/").json()["items"][0]
    assert item["total_reviews"] == 0
    assert Decimal(str(item["average_rating"])) == Decimal("0")


# ── 3. Exclusão de produto/variante vendidos → erro de domínio (409), não 500 ──

def test_excluir_variante_vendida_levanta_variant_in_use(paid_item, variant):
    with pytest.raises(VariantInUse):
        delete_variant_for_admin(variant.variant_id)
    assert ProductVariant.objects.filter(pk=variant.pk).exists()


def test_excluir_produto_vendido_levanta_product_in_use(paid_item, variant):
    with pytest.raises(ProductInUse):
        delete_product_for_admin(variant.product_id.product_id)


def test_excluir_variante_nunca_vendida_funciona(other_variant):
    delete_variant_for_admin(other_variant.variant_id)
    assert not ProductVariant.objects.filter(pk=other_variant.pk).exists()


# ── 8. Estorno repõe estoque se a mercadoria ainda não saiu ───────────────────

def test_estorno_sem_etiqueta_repoe_estoque(paid_item, variant, order):
    variant.stock = 3  # já debitado no pagamento (5 - 2)
    variant.save()

    assert order_service.refund_order(order.order_id) is True

    variant.refresh_from_db()
    order.refresh_from_db()
    assert variant.stock == 5
    assert order.order_status == Order.StatusOrder.REFUNDED


def test_estorno_de_pedido_ja_enviado_nao_repoe_estoque(paid_item, variant, order):
    variant.stock = 3
    variant.save()
    Order.objects.filter(pk=order.pk).update(shipping_status=Order.ShippingStatus.SHIPPED)

    assert order_service.refund_order(order.order_id) is True

    variant.refresh_from_db()
    assert variant.stock == 3


def test_estorno_duplicado_e_idempotente(paid_item, variant, order):
    variant.stock = 3
    variant.save()
    assert order_service.refund_order(order.order_id) is True
    assert order_service.refund_order(order.order_id) is False
    variant.refresh_from_db()
    assert variant.stock == 5  # repôs uma única vez


def test_estorno_acima_do_valor_da_cobranca_e_recusado(monkeypatch, user, order, pending_payment):
    from luxury_fashion.apps.core.exceptions import PaymentNotRefundable

    Payment.objects.filter(pk=pending_payment.pk).update(status=Payment.PaymentStatus.RECEIVED)
    fake = MagicMock()
    monkeypatch.setattr(payment_service, "AsaasClient", MagicMock(return_value=fake))

    with pytest.raises(PaymentNotRefundable):
        payment_service.refund_payment(
            user.user_id, pending_payment.payment_id, pending_payment.value + Decimal("1.00"), None
        )
    fake.refund_payment.assert_not_called()


# ── 9. Estoque do admin ───────────────────────────────────────────────────────

def test_ajuste_e_definicao_de_estoque_do_admin(variant):
    assert adjust_variant_stock_for_admin(variant.variant_id, 3).stock == 8
    assert set_variant_stock_for_admin(variant.variant_id, 1).stock == 1


def test_ajuste_que_deixa_estoque_negativo_e_recusado(variant):
    from luxury_fashion.apps.core.exceptions.cart_exception import InsufficientStock

    with pytest.raises(InsufficientStock):
        adjust_variant_stock_for_admin(variant.variant_id, -99)
    variant.refresh_from_db()
    assert variant.stock == 5


# ── Carrinho e pedidos (contrato) ─────────────────────────────────────────────

def test_carrinho_nao_expoe_mais_campos_de_frete(client, user, client_profile, cart, cart_item):
    body = client.get("/api/cart/", **auth_header(user)).json()
    assert "total_shipping" not in body and "total_geral" not in body
    assert "shipping_value" not in body["items"][0]
    assert "total_price" in body


def test_lista_de_pedidos_e_paginada(client, user, client_profile, address):
    for _ in range(3):
        Order.objects.create(user_id=user, shipping_address=address, total_geral=Decimal("10.00"))
    body = client.get("/api/orders/?page=1&page_size=2", **auth_header(user)).json()
    assert body["total"] == 3 and body["pages"] == 2 and len(body["items"]) == 2


# ── Via HTTP (rotas) ──────────────────────────────────────────────────────────

@pytest.fixture
def admin(db):
    from luxury_fashion.apps.accounts.models.user_model import User

    return User.objects.create_superuser(email="admin-audit@example.com", password="senha-super-segura-123")


def test_api_excluir_variante_vendida_da_409(client, admin, paid_item, variant):
    resp = client.delete(f"/api/products/variants/{variant.variant_id}", **auth_header(admin))
    assert resp.status_code == 409
    assert "desative" in resp.json()["detail"].lower()


def test_api_excluir_produto_vendido_da_409(client, admin, paid_item, variant):
    resp = client.delete(f"/api/products/{variant.product_id.product_id}", **auth_header(admin))
    assert resp.status_code == 409


def test_api_excluir_variante_inexistente_da_404(client, admin):
    resp = client.delete(f"/api/products/variants/{uuid.uuid4()}", **auth_header(admin))
    assert resp.status_code == 404


def test_api_avaliar_pedido_nao_entregue_da_409(client, user, client_profile, paid_item):
    resp = client.post(
        "/api/reviews/", data={"order_item_id": str(paid_item.order_item_id), "reviews": 5},
        content_type="application/json", **auth_header(user),
    )
    assert resp.status_code == 409
    assert "entregue" in resp.json()["detail"].lower()


def test_api_patch_e_delete_de_endereco_com_pedido(client, user, client_profile, address, order):
    resp = client.patch(
        f"/api/address/my-addresses/{address.address_id}", data={"street": "Rua Nova"},
        content_type="application/json", **auth_header(user),
    )
    assert resp.status_code == 200
    novo = resp.json()["address_id"]
    assert novo != str(address.address_id)

    resp = client.delete(f"/api/address/my-addresses/{novo}", **auth_header(user))
    assert resp.status_code in (200, 204)


def test_ordenacao_recente_e_avaliacao_e_filtros_basicos(product_category, variant, other_variant):
    assert filter_products(sort="recent").count() == 1
    assert filter_products(sort="rating").count() == 1
    assert filter_products(sort="name").count() == 1
    assert filter_products(search="vestido").count() == 1
    assert filter_products(search="zzz").count() == 0
    assert filter_products(product_category_id=product_category.pk).count() == 1
    assert filter_products(gender="feminino").count() + filter_products(gender="masculino").count() >= 1
    assert filter_products(in_stock_only=True).count() == 1
    assert filter_products(min_price=Decimal("0"), max_price=Decimal("100000")).count() == 1


def test_review_de_item_sem_avaliacao_autorizada_retorna_lista_vazia(client, paid_item):
    resp = client.get(f"/api/reviews/order-items/{paid_item.order_item_id}")
    assert resp.status_code == 200 and resp.json() == []

# ── Itens de carrinho/pedido trazem nome, capa e link do produto ──────────────

def _add_images(product, *, cover_name=None, others=()):
    from luxury_fashion.apps.products.models.product_image_model import ProductImage

    for i, name in enumerate(others):
        ProductImage.objects.create(product_id=product, product_image=name, display_order=i + 1)
    if cover_name:
        ProductImage.objects.create(product_id=product, product_image=cover_name, is_cover=True, display_order=9)


def test_item_do_carrinho_traz_nome_link_e_capa_do_produto(client, user, client_profile, cart, cart_item, variant):
    _add_images(variant.product_id, cover_name="products/capa.jpg", others=("products/outra.jpg",))

    item = client.get("/api/cart/", **auth_header(user)).json()["items"][0]["variant"]

    assert item["product_name"] == "Vestido Longo"
    assert item["product_id"] == str(variant.product_id.product_id)
    assert item["cover_image_url"].endswith("products/capa.jpg")  # a marcada como capa, não a primeira


def test_capa_cai_na_primeira_imagem_quando_nenhuma_e_marcada_e_none_sem_imagens(client, user, client_profile, cart, cart_item, variant):
    body = client.get("/api/cart/", **auth_header(user)).json()
    assert body["items"][0]["variant"]["cover_image_url"] is None

    _add_images(variant.product_id, others=("products/a.jpg", "products/b.jpg"))
    body = client.get("/api/cart/", **auth_header(user)).json()
    assert body["items"][0]["variant"]["cover_image_url"].endswith("products/a.jpg")


def test_item_do_pedido_traz_capa_e_link_do_produto(client, user, client_profile, paid_item, variant, order):
    _add_images(variant.product_id, cover_name="products/capa.jpg")

    body = client.get(f"/api/orders/{order.order_id}", **auth_header(user)).json()
    v = body["items"][0]["variant"]

    assert v["product_id"] == str(variant.product_id.product_id)
    assert v["cover_image_url"].endswith("products/capa.jpg")
    assert body["items"][0]["product_name"] == "Vestido Longo"  # snapshot da compra


def test_carrinho_com_varios_itens_nao_faz_query_por_item(client, user, client_profile, cart, product, django_assert_max_num_queries):
    for n, size in enumerate(["PP", "P", "G", "GG", "XG", "XXG"]):
        v = ProductVariant.objects.create(product_id=product, sku=f"Q-{n}", size=size, color="blue", price=Decimal("10.00"), stock=9)
        from luxury_fashion.apps.cart.models.cart_item_model import CartItem

        CartItem.objects.create(cart_id=cart, variant_id=v, quantity_item=1)
    _add_images(product, cover_name="products/capa.jpg")
    cart.update_totals()

    with django_assert_max_num_queries(12):  # constante: não cresce com o número de itens
        resp = client.get("/api/cart/", **auth_header(user))
    assert resp.status_code == 200 and len(resp.json()["items"]) == 6