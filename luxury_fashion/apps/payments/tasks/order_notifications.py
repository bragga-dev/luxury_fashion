"""
Tasks Celery — e-mails do ciclo do pedido: recebido, pagamento confirmado, cancelado/expirado/sem estoque,
estorno e enviado. Recebem só ids (JSON) e montam o contexto dentro da task.
"""
import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.db import transaction

from luxury_fashion.apps.core.emails.sender import send_html_email
from luxury_fashion.apps.payments.emails.order_context import build_order_email_context
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.models.payment_model import Payment

logger = logging.getLogger(__name__)

def queue_email(task, *args) -> None:
    """
    Agenda a task de e-mail para DEPOIS do commit da transação corrente (sem e-mail de algo que sofreu
    rollback). `robust=True`: se o broker estiver fora, só loga — nunca derruba pagamento/pedido
    (mesmo critério do app notifications).
    """
    transaction.on_commit(
        lambda: task.delay(*[str(a) if isinstance(a, uuid.UUID) else a for a in args]),
        robust=True,
    )


_TEMPLATES = {
    "received": "payment/emails/order_received.html",
    "confirmed": "payment/emails/payment_confirmed.html",
    "cancelled": "payment/emails/order_cancelled.html",
    "refunded": "payment/emails/payment_refunded.html",
    "shipped": "payment/emails/order_shipped.html",
    "delivered": "payment/emails/order_delivered.html",
}


def _get_order(order_id) -> Order | None:
    order = (
        Order.objects.select_related("user_id", "shipping_address")
        .filter(pk=order_id)
        .first()
    )
    if order is None:
        logger.error("E-mail de pedido não enviado: pedido %s inexistente. Task não será reagendada.", order_id)
    return order


def _send(order: Order, *, subject: str, template: str, extra: dict | None = None) -> None:
    send_html_email(
        subject=subject,
        to_email=order.user_id.email,
        template_name=template,
        context={**build_order_email_context(order), **(extra or {})},
    )
    logger.info("E-mail '%s' enviado (pedido=%s)", template, order.code)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_received_email(self, order_id: str) -> None:
    order = _get_order(order_id)
    if order is None:
        return
    try:
        _send(order, subject=f"Pedido {order.code} recebido — {settings.STORE_NAME}", template=_TEMPLATES["received"])
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de pedido recebido (pedido=%s)", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_confirmed_email(self, order_id: str) -> None:
    order = _get_order(order_id)
    if order is None:
        return
    try:
        _send(order, subject=f"Pagamento confirmado — pedido {order.code}", template=_TEMPLATES["confirmed"])
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de pagamento confirmado (pedido=%s)", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_cancelled_email(self, order_id: str, kind: str, reason: str | None = None) -> None:
    """kind: 'client' (cancelado pelo cliente) | 'expired' (sem pagamento no prazo) | 'no_stock' (pago, mas esgotou)."""
    order = _get_order(order_id)
    if order is None:
        return
    try:
        _send(
            order,
            subject=f"Pedido {order.code} cancelado — {settings.STORE_NAME}",
            template=_TEMPLATES["cancelled"],
            extra={"kind": kind, "cancel_reason": reason},
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de pedido cancelado (pedido=%s)", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_refunded_email(self, payment_id: str, kind: str, value: str | None = None) -> None:
    """kind: 'requested' (estorno pedido pelo cliente/admin) | 'late_payment' (pagamento caiu em pedido já cancelado)."""
    payment = Payment.objects.select_related("order_id").filter(pk=payment_id).first()
    if payment is None:
        logger.error("E-mail de estorno não enviado: pagamento %s inexistente.", payment_id)
        return
    order = _get_order(payment.order_id_id)
    if order is None:
        return
    try:
        _send(
            order,
            subject=f"Estorno solicitado — pedido {order.code}",
            template=_TEMPLATES["refunded"],
            extra={
                "kind": kind,
                "refund_value": value if value is not None else payment.value,
                "payment_billing_type": payment.billing_type,
            },
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de estorno (pagamento=%s)", payment_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_shipped_email(self, order_id: str) -> None:
    order = _get_order(order_id)
    if order is None:
        return
    try:
        _send(order, subject=f"Seu pedido {order.code} foi enviado — {settings.STORE_NAME}", template=_TEMPLATES["shipped"])
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de pedido enviado (pedido=%s)", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_delivered_email(self, order_id: str) -> None:
    order = _get_order(order_id)
    if order is None:
        return
    try:
        _send(order, subject=f"Seu pedido {order.code} foi entregue — {settings.STORE_NAME}", template=_TEMPLATES["delivered"])
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de pedido entregue (pedido=%s)", order_id)
        raise self.retry(exc=exc)