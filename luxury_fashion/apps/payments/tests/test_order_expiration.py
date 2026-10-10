"""Estoque debitado só no pagamento, expiração de pedidos PENDING, pagamento órfão e regras de estorno."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from luxury_fashion.apps.core.exceptions import AsaasAPIError, PaymentNotRefundable
from luxury_fashion.apps.payments.integrations.asaas_client import AsaasClient
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.services.order_service import (
    cancel_order_by_client,
    confirm_order_payment,
    expire_pending_order,
)
from luxury_fashion.apps.payments.services.payment_service import (
    handle_asaas_webhook,
    refund_payment,
    refund_payment_as_admin,
)
from luxury_fashion.apps.payments.tasks.expire_pending_orders import expire_pending_orders

pytestmark = pytest.mark.django_db


@pytest.fixture
def order_with_item(order, variant):
    OrderItem.objects.create(order_id=order, variant_id=variant, order_item_quantity=2, order_item_price=Decimal("99.95"))
    return order


@pytest.fixture
def asaas(monkeypatch):
    mock = MagicMock()
    mock.cancel_payment.return_value = {"deleted": True}
    mock.refund_payment.return_value = {"status": "REFUNDED"}
    monkeypatch.setattr(AsaasClient, "__new__", lambda cls, *a, **k: mock)
    return mock


# ── expiração ────────────────────────────────────────────────────────────

def test_expire_cancela_pedido_anula_cobranca_e_nao_mexe_no_estoque(order_with_item, pending_payment, variant, asaas):
    estoque_antes = variant.stock

    assert expire_pending_order(order_with_item.order_id) is True

    order_with_item.refresh_from_db()
    variant.refresh_from_db()
    pending_payment.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.CANCELLED
    assert variant.stock == estoque_antes  # pedido pendente nunca debitou
    assert pending_payment.status == Payment.PaymentStatus.CANCELLED
    asaas.cancel_payment.assert_called_once_with(pending_payment.asaas_payment_id)


def test_expire_ignora_pedido_que_nao_esta_pendente(order_with_item, variant, asaas):
    order_with_item.order_status = Order.StatusOrder.COMPLETED
    order_with_item.save()
    estoque = variant.stock

    assert expire_pending_order(order_with_item.order_id) is False
    variant.refresh_from_db()
    assert variant.stock == estoque


def test_expire_reverte_tudo_se_a_asaas_recusar_anular(order_with_item, pending_payment, variant, asaas):
    asaas.cancel_payment.side_effect = AsaasAPIError("cobrança já paga")
    estoque = variant.stock

    with pytest.raises(AsaasAPIError):
        expire_pending_order(order_with_item.order_id)

    order_with_item.refresh_from_db()
    variant.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.PENDING
    assert variant.stock == estoque


def test_task_so_expira_pedidos_acima_do_prazo(order_with_item, other_variant, user, address, settings, asaas):
    settings.ORDER_PENDING_EXPIRATION_HOURS = 48
    novo = Order.objects.create(
        user_id=user, shipping_address=address, subtotal=Decimal("10"),
        order_shipping_total=Decimal("0"), total_geral=Decimal("10"),
    )
    Order.objects.filter(pk=order_with_item.pk).update(created_at=timezone.now() - timedelta(hours=49))

    assert expire_pending_orders() == 1

    order_with_item.refresh_from_db()
    novo.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.CANCELLED
    assert novo.order_status == Order.StatusOrder.PENDING


# ── estoque debitado só quando o pagamento é efetivado ───────────────────

def test_pagamento_efetivado_debita_estoque_e_conclui(order_with_item, variant):
    estoque = variant.stock

    assert confirm_order_payment(order_with_item.order_id) is True

    order_with_item.refresh_from_db()
    variant.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.COMPLETED
    assert variant.stock == estoque - 2


def test_confirmacao_duplicada_nao_debita_duas_vezes(order_with_item, variant):
    estoque = variant.stock
    confirm_order_payment(order_with_item.order_id)
    assert confirm_order_payment(order_with_item.order_id) is True
    variant.refresh_from_db()
    assert variant.stock == estoque - 2


def test_sem_estoque_na_confirmacao_cancela_sem_debitar(order_with_item, variant):
    variant.stock = 1  # outro cliente pagou antes pela última unidade
    variant.save()

    assert confirm_order_payment(order_with_item.order_id) is False

    order_with_item.refresh_from_db()
    variant.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.CANCELLED
    assert variant.stock == 1


def test_webhook_sem_estoque_estorna_automaticamente(order_with_item, pending_payment, variant, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    variant.stock = 0
    variant.save()

    handle_asaas_webhook("tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})

    order_with_item.refresh_from_db()
    assert order_with_item.order_status == Order.StatusOrder.CANCELLED
    assert asaas.refund_payment.call_count == 1


def test_webhook_de_pagamento_debita_estoque(order_with_item, pending_payment, variant, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    estoque = variant.stock

    handle_asaas_webhook("tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})
    handle_asaas_webhook("tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})  # reenvio

    variant.refresh_from_db()
    assert variant.stock == estoque - 2
    asaas.refund_payment.assert_not_called()


def test_cancelar_pedido_pendente_nao_mexe_no_estoque(user, order_with_item, variant):
    estoque = variant.stock
    cancel_order_by_client(user.user_id, order_with_item.order_id, "desisti")
    variant.refresh_from_db()
    assert variant.stock == estoque


# ── pagamento órfão ──────────────────────────────────────────────────────

def test_pagamento_em_pedido_cancelado_estorna_sem_estourar(order, pending_payment, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    order.order_status = Order.StatusOrder.CANCELLED
    order.save()

    handle_asaas_webhook("tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})

    order.refresh_from_db()
    pending_payment.refresh_from_db()
    assert order.order_status == Order.StatusOrder.CANCELLED
    assert asaas.refund_payment.call_count == 1
    assert pending_payment.status == "REFUNDED"


def test_pagamento_em_pedido_pendente_continua_concluindo(order, pending_payment, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    handle_asaas_webhook("tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})
    order.refresh_from_db()
    assert order.order_status == Order.StatusOrder.COMPLETED
    asaas.refund_payment.assert_not_called()


# ── estorno ──────────────────────────────────────────────────────────────

@pytest.fixture
def paid_payment(order, pending_payment):
    order.order_status = Order.StatusOrder.COMPLETED
    order.save()
    pending_payment.status = Payment.PaymentStatus.RECEIVED
    pending_payment.save()
    return pending_payment


def test_cliente_estorna_enquanto_nao_ha_etiqueta(user, order, paid_payment, asaas):
    refund_payment(user.user_id, paid_payment.payment_id, None, "arrependimento")
    asaas.refund_payment.assert_called_once()


def test_cliente_nao_estorna_depois_da_etiqueta(user, order, paid_payment, asaas):
    order.frenet_order_id = "12345"
    order.shipping_status = Order.ShippingStatus.LABEL_GENERATED
    order.save()
    with pytest.raises(PaymentNotRefundable):
        refund_payment(user.user_id, paid_payment.payment_id, None, None)
    asaas.refund_payment.assert_not_called()


def test_admin_estorna_mesmo_depois_do_envio(order, paid_payment, asaas):
    order.shipping_status = Order.ShippingStatus.SHIPPED
    order.save()
    refund_payment_as_admin(paid_payment.payment_id, None, "devolução")
    asaas.refund_payment.assert_called_once()