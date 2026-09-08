"""
Tasks Celery — envio de e-mails de pagamento (solicitação de pagamento ao cliente).
"""

import logging
import uuid
from celery import shared_task

from luxury_fashion.apps.accounts.selectors.client_selector import get_client_by_user_id
from luxury_fashion.apps.accounts.selectors.user_selector import get_user_by_id
from luxury_fashion.apps.core.emails.sender import send_html_email
from luxury_fashion.apps.products.emails.product_context import (
    client_orders_url,
    resolve_client_display_name,
    store_url,
)
from luxury_fashion.apps.payments.selectors.payment_selector import get_payment_by_id
from luxury_fashion.apps.payments.selectors.asaas_customer_selector import get_asaas_customer_by_client_id
from luxury_fashion.apps.payments.emails.payment_context import (
    build_payment_block,
)
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_payment_request(self, user_id: uuid.UUID, payment_id: uuid.UUID) -> None:
    """
    Envia o e-mail de solicitação de pagamento para confirmação do pedido.
    """
    user = get_user_by_id(user_id=user_id)
    payment = get_payment_by_id(payment_id=payment_id)

    if user is None or payment is None:
        logger.error(
            "Não foi possível enviar e-mail de pagamento: user ou payment inexistente "
            "(user=%s, payment=%s). Task não será reagendada.",
            user_id, payment_id,
        )
        return

    client = get_client_by_user_id(user_id=user_id)
    customer = get_asaas_customer_by_client_id(client.client_id) if client else None
    if customer is None:
        logger.error(
            "Não foi possível enviar e-mail de pagamento: cliente Asaas não encontrado "
            "(user=%s, payment=%s). Task não será reagendada.",
            user_id, payment_id,
        )
        return

    try:
        context = {
            "client_name": resolve_client_display_name(user),
            "user_email": user.email,

            **build_payment_block(payment=payment, customer=customer),

            "client_orders_url": client_orders_url(),
            "store_url": store_url(),
        }

        send_html_email(
            subject="Pagamento — ÉLUXO MODAS",
            to_email=user.email,
            template_name="payment/emails/send_payment_request.html",
            context=context,
        )

        logger.info("Payment confirmation email sent to %s (payment=%s)", user.email, payment.payment_id)

    except Exception as exc:
        logger.exception("Error sending payment confirmation email (user=%s, payment=%s)", user_id, payment_id)
        raise self.retry(exc=exc)