"""
E-mails transacionais: cada ação do sistema que precisa avisar o usuário dispara o e-mail certo, uma única vez,
para o destinatário certo; todos os templates renderizam e as tasks estão registradas no worker do Celery.
"""
import json
import os
import subprocess
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.services import auth_service, user_service
from luxury_fashion.apps.accounts.services.verification import verify_email
from luxury_fashion.apps.core.emails.sender import send_html_email
from luxury_fashion.apps.notifications.models.notification_model import Notification
from luxury_fashion.apps.payments.integrations.asaas_client import AsaasClient
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment
from luxury_fashion.apps.payments.schemas.order_schema import OrderCreateIn
from luxury_fashion.apps.payments.services import frenet_webhook_service
from luxury_fashion.apps.payments.services.order_delivery_service import mark_order_as_delivered
from luxury_fashion.apps.payments.services.order_service import (
    cancel_order_by_client,
    confirm_order_payment,
    create_order_from_cart,
    expire_pending_order,
)
from luxury_fashion.apps.payments.services.payment_service import handle_asaas_webhook, refund_payment
from luxury_fashion.apps.website.models.contact_model import Contact
from luxury_fashion.apps.website.schemas.contact_schema import ContactCreateIn
from luxury_fashion.apps.website.services.contact_service import create_contact_message

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _loja(settings):
    settings.STORE_NAME = "Gama Fashion"
    settings.CONTACT_NOTIFICATION_EMAIL = "loja@example.com"


@pytest.fixture
def run(django_capture_on_commit_callbacks):
    """Executa os callbacks on_commit (onde as tasks de e-mail são disparadas) — Celery roda eager nos testes."""
    def _run(fn, *args, **kwargs):
        with django_capture_on_commit_callbacks(execute=True):
            return fn(*args, **kwargs)
    return _run


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


def only(mailoutbox, *, to, subject_has):
    assert len(mailoutbox) == 1, [m.subject for m in mailoutbox]
    mail = mailoutbox[0]
    assert mail.to == [to]
    assert subject_has.lower() in mail.subject.lower(), mail.subject
    assert "Gama Fashion" in mail.subject or "Gama Fashion" in mail.alternatives[0][0]
    return mail


def html(mail) -> str:
    return mail.alternatives[0][0]


# ── conta ────────────────────────────────────────────────────────────────

def _verification_link(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def test_boas_vindas_so_na_primeira_confirmacao_do_email(run, mailoutbox, user, client_profile):
    user.is_active = False
    user.is_trusty = False
    user.save()
    uid, token = _verification_link(user)

    run(verify_email, uid, token)
    mail = only(mailoutbox, to=user.email, subject_has="Bem-vinda")
    assert "Maria" in html(mail)

    run(verify_email, uid, token)  # clicou de novo no link
    assert len(mailoutbox) == 1


def test_senha_alterada_avisa_por_email(run, mailoutbox, user, client_profile):
    run(auth_service.change_password, user, "senha-super-segura-123", "Nova-Senha-Forte-2026!")
    mail = only(mailoutbox, to=user.email, subject_has="senha foi alterada")
    assert "/esqueci-senha" in html(mail)  # CTA de redefinição para quem não reconhece a troca


def test_redefinicao_de_senha_tambem_avisa(run, mailoutbox, user, client_profile):
    uid, token = _verification_link(user)
    run(auth_service.confirm_password_reset, uid.rstrip("="), token, "Outra-Senha-Forte-2026!")
    only(mailoutbox, to=user.email, subject_has="senha foi alterada")


def test_senha_errada_nao_dispara_email(run, mailoutbox, user, client_profile):
    with pytest.raises(Exception):
        run(auth_service.change_password, user, "errada", "Nova-Senha-Forte-2026!")
    assert mailoutbox == []


def test_exclusao_de_conta_confirma_no_email_original(run, mailoutbox, user, client_profile):
    email = user.email
    run(user_service.delete_own_account, user, "senha-super-segura-123")
    mail = only(mailoutbox, to=email, subject_has="conta foi excluída")
    assert "O que mantemos" not in html(mail)  # sem pedidos: nada retido


def test_exclusao_com_pedidos_explica_o_que_fica_guardado(run, mailoutbox, user, client_profile, address, order):
    email = user.email
    run(user_service.delete_own_account, user, "senha-super-segura-123")
    mail = only(mailoutbox, to=email, subject_has="conta foi excluída")
    assert "O que mantemos" in html(mail)


def test_desativar_e_reativar_conta_avisam(run, mailoutbox, user, client_profile):
    run(user_service.deactivate_account, user.user_id)
    only(mailoutbox, to=user.email, subject_has="desativada")
    mailoutbox.clear()
    run(user_service.reactivate_user, user.user_id)
    only(mailoutbox, to=user.email, subject_has="reativada")


# ── pedido ───────────────────────────────────────────────────────────────

def test_pedido_recebido_no_checkout(run, mailoutbox, user, client_profile, address, cart, cart_item, variant_shipping, frenet_calls):
    result = run(create_order_from_cart, user_id=user.user_id,
                 data=OrderCreateIn(shipping_address_id=address.address_id, shipping_service_code="04510"))
    mail = only(mailoutbox, to=user.email, subject_has=result.code)
    body = html(mail)
    assert "Aguardando pagamento" in body
    assert "Rua das Flores" in body            # endereço de entrega
    assert "PAC" in body or "Correios" in body  # serviço de frete gravado no pedido


def test_pagamento_confirmado_debita_estoque_e_avisa_uma_vez(run, mailoutbox, user, client_profile, order_with_item):
    assert run(confirm_order_payment, order_with_item.order_id) is True
    mail = only(mailoutbox, to=user.email, subject_has="Pagamento confirmado")
    assert order_with_item.code in html(mail)

    run(confirm_order_payment, order_with_item.order_id)  # webhook duplicado
    assert len(mailoutbox) == 1


def test_pagamento_confirmado_gera_email_E_notificacao_in_app(run, mailoutbox, user, client_profile, order_with_item):
    run(confirm_order_payment, order_with_item.order_id)
    assert len(mailoutbox) == 1
    assert Notification.objects.filter(recipient=user, type=Notification.NotificationType.ORDER_PAID).count() == 1


def test_sem_estoque_na_confirmacao_avisa_que_havera_estorno(run, mailoutbox, user, client_profile, order_with_item, variant):
    variant.stock = 0
    variant.save()
    assert run(confirm_order_payment, order_with_item.order_id) is False
    mail = only(mailoutbox, to=user.email, subject_has="cancelado")
    assert "estornado integralmente" in html(mail)


def test_cancelamento_pelo_cliente_mostra_o_motivo(run, mailoutbox, user, client_profile, order_with_item):
    run(cancel_order_by_client, user.user_id, order_with_item.order_id, "Mudei de ideia")
    mail = only(mailoutbox, to=user.email, subject_has="cancelado")
    assert "Mudei de ideia" in html(mail)


def test_pedido_expirado_avisa(run, mailoutbox, user, client_profile, order_with_item, asaas):
    assert run(expire_pending_order, order_with_item.order_id) is True
    mail = only(mailoutbox, to=user.email, subject_has="cancelado")
    assert "prazo" in html(mail)


@pytest.fixture
def paid_payment(order_with_item, pending_payment):
    order_with_item.order_status = Order.StatusOrder.COMPLETED
    order_with_item.save()
    pending_payment.status = Payment.PaymentStatus.RECEIVED
    pending_payment.save()
    return pending_payment


def test_estorno_pedido_pelo_cliente_avisa(run, mailoutbox, user, client_profile, paid_payment, asaas):
    run(refund_payment, user.user_id, paid_payment.payment_id, None, "arrependimento")
    mail = only(mailoutbox, to=user.email, subject_has="Estorno solicitado")
    assert "Detalhes do estorno" in html(mail)


def test_pagamento_em_pedido_cancelado_estorna_e_avisa(run, mailoutbox, user, client_profile, order, pending_payment, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    order.order_status = Order.StatusOrder.CANCELLED
    order.save()
    run(handle_asaas_webhook, "tok", "PAYMENT_RECEIVED", {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"})
    mail = only(mailoutbox, to=user.email, subject_has="Estorno solicitado")
    assert "não pôde" in html(mail)


def test_webhook_de_estorno_de_pagamento_orfao_nao_estoura_nem_notifica_reembolso(run, user, client_profile, order, pending_payment, settings, asaas):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    order.order_status = Order.StatusOrder.CANCELLED
    order.save()

    run(handle_asaas_webhook, "tok", "PAYMENT_REFUNDED", {"id": pending_payment.asaas_payment_id, "status": "REFUNDED"})

    order.refresh_from_db()
    assert order.order_status == Order.StatusOrder.CANCELLED
    assert not Notification.objects.filter(recipient=user, type=Notification.NotificationType.ORDER_REFUNDED).exists()


def test_webhook_de_estorno_de_pedido_pago_continua_marcando_reembolsado(run, user, client_profile, paid_payment, settings):
    settings.ASAAS_WEBHOOK_TOKEN = "tok"
    run(handle_asaas_webhook, "tok", "PAYMENT_REFUNDED", {"id": paid_payment.asaas_payment_id, "status": "REFUNDED"})
    paid_payment.order_id.refresh_from_db()
    assert paid_payment.order_id.order_status == Order.StatusOrder.REFUNDED
    assert Notification.objects.filter(recipient=user, type=Notification.NotificationType.ORDER_REFUNDED).count() == 1


# ── envio ────────────────────────────────────────────────────────────────

@pytest.fixture
def labeled_order(order_with_item):
    order_with_item.frenet_order_id = "12682"
    order_with_item.shipping_status = Order.ShippingStatus.LABEL_GENERATED
    order_with_item.shipping_tracking_code = "AA123456789BR"
    order_with_item.shipping_service_name = "Correios - PAC"
    order_with_item.shipping_delivery_days = 6
    order_with_item.save()
    return order_with_item


def test_pedido_enviado_avisa_com_rastreio_so_na_primeira_vez(run, mailoutbox, user, client_profile, labeled_order):
    run(frenet_webhook_service.handle_status_update, labeled_order.code, 12682, frenet_webhook_service.SHIPMENT_POSTED)
    mail = only(mailoutbox, to=user.email, subject_has="foi enviado")
    assert "AA123456789BR" in html(mail)

    run(frenet_webhook_service.handle_status_update, labeled_order.code, 12682, frenet_webhook_service.SHIPMENT_POSTED)
    assert len(mailoutbox) == 1  # a Frenet reenvia o evento


def test_entrega_manual_pelo_admin_avisa_uma_vez(run, mailoutbox, user, client_profile, labeled_order):
    labeled_order.order_status = Order.StatusOrder.COMPLETED
    labeled_order.shipping_status = Order.ShippingStatus.SHIPPED
    labeled_order.save()

    run(mark_order_as_delivered, labeled_order.order_id)
    mail = only(mailoutbox, to=user.email, subject_has="foi entregue")
    assert "Avaliar minha compra" in html(mail)
    assert Notification.objects.filter(recipient=user, type=Notification.NotificationType.ORDER_DELIVERED).count() == 1

    run(mark_order_as_delivered, labeled_order.order_id)  # idempotente: sem novo e-mail
    assert len(mailoutbox) == 1


def test_entrega_pelo_webhook_da_frenet_avisa(run, mailoutbox, user, client_profile, labeled_order, settings):
    settings.FRENET_SHIPMENT_DELIVERED_STATUS = 7
    labeled_order.order_status = Order.StatusOrder.COMPLETED
    labeled_order.shipping_status = Order.ShippingStatus.IN_TRANSIT
    labeled_order.save()

    run(frenet_webhook_service.handle_status_update, labeled_order.code, 12682, 7)
    only(mailoutbox, to=user.email, subject_has="foi entregue")

    run(frenet_webhook_service.handle_status_update, labeled_order.code, 12682, 7)  # evento duplicado
    assert len(mailoutbox) == 1


def test_em_transporte_so_gera_notificacao_in_app_nunca_email(run, mailoutbox, user, client_profile, labeled_order):
    labeled_order.shipping_status = Order.ShippingStatus.SHIPPED
    labeled_order.save()
    run(frenet_webhook_service.handle_tracking_update, labeled_order.code, 12682, "AA123456789BR")
    assert mailoutbox == []
    assert Notification.objects.filter(recipient=user, type=Notification.NotificationType.ORDER_IN_TRANSIT).count() == 1


def test_etiqueta_cancelada_nao_avisa_o_cliente(run, mailoutbox, user, client_profile, labeled_order):
    run(frenet_webhook_service.handle_status_update, labeled_order.code, 12682, frenet_webhook_service.SHIPMENT_CANCELLED)
    assert mailoutbox == []


# ── contato ──────────────────────────────────────────────────────────────

def test_contato_confirma_ao_cliente_e_avisa_a_loja(run, mailoutbox):
    run(create_contact_message, ContactCreateIn(
        full_name="Ana Souza", subject="Troca de tamanho", message="Oi!\nPreciso trocar.", email="ana@example.com", phone="75999999999",
    ))
    destinos = {m.to[0]: m for m in mailoutbox}
    assert set(destinos) == {"ana@example.com", "loja@example.com"}
    assert "Recebemos sua mensagem" in destinos["ana@example.com"].subject
    assert "Novo contato" in destinos["loja@example.com"].subject
    assert "mailto:ana@example.com" in html(destinos["loja@example.com"])


def test_contato_sem_email_de_aviso_configurado_so_confirma_ao_cliente(run, mailoutbox, settings):
    settings.CONTACT_NOTIFICATION_EMAIL = ""
    run(create_contact_message, ContactCreateIn(
        full_name="Bia", subject="Oi", message="x", email="bia@example.com", phone="75999999999",
    ))
    assert [m.to[0] for m in mailoutbox] == ["bia@example.com"]


# ── renderização de todos os templates ───────────────────────────────────

def _contexts(order_with_item):
    from luxury_fashion.apps.payments.emails.order_context import build_order_email_context
    base = {"store_name": "Gama Fashion", "support_email": "suporte@example.com", "client_name": "Maria",
            "user_email": "maria@example.com", "store_url": "https://loja.example/", "client_orders_url": "https://loja.example/pedidos"}
    order_ctx = build_order_email_context(order_with_item)
    contact = {"contact_name": "Ana", "contact_email": "ana@example.com", "contact_phone": "75999999999",
               "contact_subject": "Oi", "contact_message": "linha 1\nlinha 2", "reply_url": "mailto:ana@example.com"}
    return {
        "accounts/emails/welcome_email.html": base,
        "accounts/emails/password_changed.html": {**base, "changed_at": timezone.now(), "forgot_password_url": "https://x/esqueci-senha"},
        "accounts/emails/account_deleted.html": {**base, "kept_orders": True},
        "accounts/emails/account_status.html": {**base, "kind": "deactivated"},
        "accounts/emails/verification_email.html": {**base, "verify_url": "https://x/verify"},
        "accounts/emails/password_reset.html": {**base, "reset_url": "https://x/reset"},
        "payment/emails/order_received.html": {**base, **order_ctx},
        "payment/emails/payment_confirmed.html": {**base, **order_ctx},
        "payment/emails/order_cancelled.html": {**base, **order_ctx, "kind": "client", "cancel_reason": "x"},
        "payment/emails/payment_refunded.html": {**base, **order_ctx, "kind": "requested", "refund_value": Decimal("10"), "payment_billing_type": "PIX"},
        "payment/emails/order_shipped.html": {**base, **order_ctx, "order_tracking_code": "AA1BR"},
        "payment/emails/order_delivered.html": {**base, **order_ctx},
        "website/emails/contact_received.html": {**base, **contact},
        "website/emails/contact_admin_alert.html": {**base, **contact},
    }


# Templates anteriores (verificação, redefinição, cobrança): marca escrita direto no HTML, no padrão do base.html.
TEMPLATES_COM_MARCA_FIXA = {
    "accounts/emails/verification_email.html",
    "accounts/emails/password_reset.html",
    "payment/emails/send_payment_request.html",
}


def test_todos_os_templates_renderizam_e_os_novos_usam_o_nome_da_loja_configurado(order_with_item):
    for name, ctx in _contexts(order_with_item).items():
        out = render_to_string(name, {**ctx, "store_name": "Loja Teste XYZ"})
        assert "{{" not in out and "{%" not in out, name
        if name in TEMPLATES_COM_MARCA_FIXA:
            assert "Gama Fashion" in out, name
        else:
            assert "Loja Teste XYZ" in out, f"{name} não usa {{{{ store_name }}}}"


def test_nenhum_template_filho_cita_a_marca_antiga_fixa():
    raiz = Path(__file__).resolve().parents[2]
    for caminho in list((raiz / "accounts/templates/accounts/emails").glob("*.html")) \
            + list((raiz / "payments/templates/payment/emails").glob("*.html")) \
            + list((raiz / "website/templates/website/emails").glob("*.html")) \
            + list((raiz / "core/templates/core/emails").glob("_*.html")):
        texto = caminho.read_text(encoding="utf-8")
        assert "Éluxo" not in texto and "ÉLUXO" not in texto, f"{caminho.name} cita a marca fixa; use {{{{ store_name }}}}"


@pytest.mark.parametrize("kind", ["client", "expired", "no_stock"])
def test_pedido_cancelado_renderiza_todas_as_variantes(order_with_item, kind):
    ctx = _contexts(order_with_item)["payment/emails/order_cancelled.html"]
    out = render_to_string("payment/emails/order_cancelled.html", {**ctx, "kind": kind})
    assert "Pedido cancelado" in out


def test_conteudo_do_usuario_e_escapado_no_email(order_with_item):
    ctx = _contexts(order_with_item)["website/emails/contact_admin_alert.html"]
    out = render_to_string("website/emails/contact_admin_alert.html", {**ctx, "contact_message": "<script>alert(1)</script>"})
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


# ── Celery: o WORKER precisa conhecer todas as tasks ─────────────────────

def test_worker_do_celery_registra_todas_as_tasks_de_email():
    code = """
import json, django
django.setup()
from luxury_fashion.config.celery import app
app.loader.import_default_modules()
print(json.dumps(sorted(t for t in app.tasks if t.startswith("luxury_fashion"))))
"""
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**os.environ}, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-1500:]
    registered = set(json.loads(out.stdout.strip().splitlines()[-1]))
    esperadas = {
        "accounts.tasks.verification_account.send_verification_email",
        "accounts.tasks.password_reset.send_password_reset_email",
        "accounts.tasks.account_notifications.send_welcome_email",
        "accounts.tasks.account_notifications.send_password_changed_email",
        "accounts.tasks.account_notifications.send_account_deleted_email",
        "accounts.tasks.account_notifications.send_account_status_email",
        "payments.tasks.send_payment_request.send_payment_request",
        "payments.tasks.expire_pending_orders.expire_pending_orders",
        "payments.tasks.order_notifications.send_order_received_email",
        "payments.tasks.order_notifications.send_payment_confirmed_email",
        "payments.tasks.order_notifications.send_order_cancelled_email",
        "payments.tasks.order_notifications.send_payment_refunded_email",
        "payments.tasks.order_notifications.send_order_shipped_email",
        "payments.tasks.order_notifications.send_order_delivered_email",
        "notifications.tasks.cleanup_notifications.cleanup_old_notifications",
        "notifications.tasks.send_review_requests.send_review_requests",
        "website.tasks.contact_notifications.send_contact_received_email",
        "website.tasks.contact_notifications.send_contact_admin_alert",
    }
    faltando = {t for t in esperadas if f"luxury_fashion.apps.{t}" not in registered}
    assert not faltando, f"tasks não registradas no worker: {sorted(faltando)}"