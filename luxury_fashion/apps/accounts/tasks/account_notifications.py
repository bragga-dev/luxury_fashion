"""
Tasks Celery — e-mails de conta: boas-vindas, senha alterada, exclusão e status (desativada/reativada).

Todas recebem só ids/strings simples (serializáveis em JSON) e montam o contexto dentro da task.
"""
import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.emails.sender import send_html_email
from luxury_fashion.apps.payments.emails.payment_context import client_orders_url, store_url
from luxury_fashion.apps.payments.emails.order_context import forgot_password_url
from luxury_fashion.apps.products.emails.product_context import resolve_client_display_name

logger = logging.getLogger(__name__)


def _user_or_none(user_id) -> User | None:
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        logger.error("E-mail de conta não enviado: usuário %s inexistente. Task não será reagendada.", user_id)
    return user


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: str) -> None:
    """Boas-vindas depois que o e-mail é confirmado (ou o cadastro via Google é criado)."""
    user = _user_or_none(user_id)
    if user is None:
        return
    try:
        send_html_email(
            subject=f"Bem-vinda(o) à {settings.STORE_NAME}!",
            to_email=user.email,
            template_name="accounts/emails/welcome_email.html",
            context={
                "client_name": resolve_client_display_name(user),
                "store_url": store_url(),
                "client_orders_url": client_orders_url(),
            },
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de boas-vindas (user=%s)", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_changed_email(self, user_id: str) -> None:
    """Aviso de segurança: a senha da conta foi trocada (troca logada ou redefinição por link)."""
    user = _user_or_none(user_id)
    if user is None:
        return
    try:
        send_html_email(
            subject=f"Sua senha foi alterada — {settings.STORE_NAME}",
            to_email=user.email,
            template_name="accounts/emails/password_changed.html",
            context={
                "client_name": resolve_client_display_name(user),
                "user_email": user.email,
                "changed_at": timezone.localtime(),
                "forgot_password_url": forgot_password_url(),
            },
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de senha alterada (user=%s)", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_account_deleted_email(self, to_email: str, client_name: str, kept_orders: bool) -> None:
    """
    Confirmação de exclusão de conta. Recebe e-mail e nome como argumentos (e não o user_id):
    quando a task roda, o registro já foi apagado ou anonimizado.
    """
    try:
        send_html_email(
            subject=f"Sua conta foi excluída — {settings.STORE_NAME}",
            to_email=to_email,
            template_name="accounts/emails/account_deleted.html",
            context={"client_name": client_name, "user_email": to_email, "kept_orders": kept_orders},
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de conta excluída")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_account_status_email(self, user_id: str, kind: str) -> None:
    """Conta desativada ou reativada por um administrador. kind: 'deactivated' | 'reactivated'."""
    user = _user_or_none(user_id)
    if user is None:
        return
    subjects = {
        "deactivated": f"Sua conta foi desativada — {settings.STORE_NAME}",
        "reactivated": f"Sua conta foi reativada — {settings.STORE_NAME}",
    }
    try:
        send_html_email(
            subject=subjects[kind],
            to_email=user.email,
            template_name="accounts/emails/account_status.html",
            context={
                "kind": kind,
                "client_name": resolve_client_display_name(user),
                "user_email": user.email,
                "store_url": store_url(),
            },
        )
    except Exception as exc:
        logger.exception("Erro ao enviar e-mail de status da conta (user=%s, kind=%s)", user_id, kind)
        raise self.retry(exc=exc)