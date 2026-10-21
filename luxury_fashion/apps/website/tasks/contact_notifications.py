"""Tasks Celery — e-mails do formulário de contato (confirmação ao cliente e aviso à loja)."""
import logging
from urllib.parse import quote

from celery import shared_task
from django.conf import settings

from luxury_fashion.apps.core.emails.sender import send_html_email
from luxury_fashion.apps.payments.emails.payment_context import store_url
from luxury_fashion.apps.website.models.contact_model import Contact

logger = logging.getLogger(__name__)


def _get_contact(contact_id) -> Contact | None:
    contact = Contact.objects.filter(pk=contact_id).first()
    if contact is None:
        logger.error("E-mail de contato não enviado: mensagem %s inexistente.", contact_id)
    return contact


def _base_context(contact: Contact) -> dict:
    return {
        "contact_name": contact.full_name,
        "contact_email": contact.email,
        "contact_phone": contact.phone,
        "contact_subject": contact.subject,
        "contact_message": contact.message,
        "store_url": store_url(),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_contact_received_email(self, contact_id: str) -> None:
    """Confirmação de recebimento para quem preencheu o formulário."""
    contact = _get_contact(contact_id)
    if contact is None:
        return
    try:
        send_html_email(
            subject=f"Recebemos sua mensagem — {settings.STORE_NAME}",
            to_email=contact.email,
            template_name="website/emails/contact_received.html",
            context=_base_context(contact),
        )
    except Exception as exc:
        logger.exception("Erro ao enviar confirmação de contato (contato=%s)", contact_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_contact_admin_alert(self, contact_id: str) -> None:
    """Aviso para a loja (CONTACT_NOTIFICATION_EMAIL) de que chegou uma mensagem nova."""
    contact = _get_contact(contact_id)
    if contact is None or not settings.CONTACT_NOTIFICATION_EMAIL:
        return
    try:
        reply_url = f"mailto:{contact.email}?subject={quote('Re: ' + contact.subject)}"
        send_html_email(
            subject=f"Novo contato: {contact.subject}",
            to_email=settings.CONTACT_NOTIFICATION_EMAIL,
            template_name="website/emails/contact_admin_alert.html",
            context={**_base_context(contact), "reply_url": reply_url},
        )
    except Exception as exc:
        logger.exception("Erro ao enviar aviso de contato à loja (contato=%s)", contact_id)
        raise self.retry(exc=exc)