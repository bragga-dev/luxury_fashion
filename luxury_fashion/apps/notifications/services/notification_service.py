"""
Service layer de Notifications.

Dois lados:
- PRODUTOR (`notify*`, `clear_*`): chamado pelos outros apps quando algo
  acontece (pagamento confirmado, pedido enviado...). Nunca levanta exceção:
  uma notificação que falha não pode derrubar pagamento/pedido.
- CONSUMIDOR (`list_*`, `mark_*`...): usado pelos endpoints /notifications.

Regra de ouro: produtores usam `*_on_commit`. A notificação só nasce depois
que a transação do pedido/pagamento foi confirmada — sem notificação de algo
que sofreu rollback.
"""
import functools
import logging
from typing import Optional
from uuid import UUID

from django.db import transaction

from luxury_fashion.apps.core.exceptions.notification_exception import NotificationNotFound
from luxury_fashion.apps.core.schemas.deafult_schema import PageOut
from luxury_fashion.apps.core.utils.pagination import paginate_queryset
from luxury_fashion.apps.notifications.models.notification_model import Notification
from luxury_fashion.apps.notifications.repositories.notification_repository import (
    bulk_create_notifications,
    create_notification,
    delete_by_target,
    delete_notification,
    mark_all_as_read,
    mark_as_read,
)
from luxury_fashion.apps.notifications.schemas.notification_schema import (
    MarkAllReadOut,
    NotificationOut,
    UnreadCountOut,
)
from luxury_fashion.apps.notifications.selectors.notification_selector import (
    count_unread,
    get_active_admin_ids,
    get_notification_for_user,
    get_notifications_for_user,
    get_order_ref,
)

logger = logging.getLogger(__name__)

NT = Notification.NotificationType
TT = Notification.TargetType

# ── Rotas do front (action_url) ──────────────────────────────────────────────
# Centralizadas aqui (mesmo padrão do beauty_formula) pra não espalhar string de
# rota do front pelos helpers. `action_url` precisa existir pro PAPEL do
# destinatário, senão o clique cai em 404.
CLIENT_ORDERS_URL = "/painel/meus-pedidos"   # rota real (a mesma usada nos e-mails)
ADMIN_ORDERS_URL = "/painel/pedidos"         # TODO: confirmar a rota admin no front
ADMIN_REVIEWS_URL = "/painel/avaliacoes"     # TODO: confirmar a rota admin no front


def _safe_action_url(url: str) -> str:
    """
    Só aceita caminho relativo (/pedidos/123). Qualquer coisa com esquema/host
    ou `//` é descartada — evita open redirect caso um dia a URL venha de fora.
    """
    url = (url or "").strip()
    if url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url[:300]
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# Produtor
# ═══════════════════════════════════════════════════════════════════════════════

def notify(
    *,
    recipient_id: UUID,
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor_id: Optional[UUID] = None,
    target_type: str = "",
    target_id: Optional[UUID] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    # Ninguém é notificado de uma ação que ele mesmo fez.
    if actor_id is not None and actor_id == recipient_id:
        return
    try:
        create_notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=_safe_action_url(action_url),
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            dedupe_key=dedupe_key,
        )
    except Exception:
        logger.exception("Falha ao criar notificação (recipient=%s, type=%s).", recipient_id, notification_type)


def notify_admins(
    *,
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor_id: Optional[UUID] = None,
    target_type: str = "",
    target_id: Optional[UUID] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    """Notifica todos os admins ativos (menos o próprio autor do evento)."""
    try:
        bulk_create_notifications(
            recipient_ids=get_active_admin_ids(exclude_id=actor_id),
            notification_type=notification_type,
            title=title,
            body=body,
            action_url=_safe_action_url(action_url),
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            dedupe_key=dedupe_key,
        )
    except Exception:
        logger.exception("Falha ao notificar admins (type=%s).", notification_type)


def clear_target_notifications(*, target_type: str, target_id: UUID, notification_type: Optional[str] = None) -> None:
    """Remove notificações pendentes de um objeto (ex.: REVIEW_PENDING já tratada por outro admin)."""
    try:
        delete_by_target(target_type=target_type, target_id=target_id, notification_type=notification_type)
    except Exception:
        logger.exception("Falha ao limpar notificações do alvo %s:%s.", target_type, target_id)


def notify_on_commit(**kwargs) -> None:
    """Agenda `notify` para depois do commit da transação corrente."""
    transaction.on_commit(lambda: notify(**kwargs), robust=True)


def notify_admins_on_commit(**kwargs) -> None:
    transaction.on_commit(lambda: notify_admins(**kwargs), robust=True)


def clear_target_notifications_on_commit(**kwargs) -> None:
    transaction.on_commit(lambda: clear_target_notifications(**kwargs), robust=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers por evento de domínio
#
# Convenção (igual ao beauty_formula): o domínio chama `notify_<evento>(id)`
# passando só o ID do objeto de origem — nunca a instância — e este módulo
# resolve o objeto, monta título/corpo/rota e cria a notificação.
#
# Todos rodam DEPOIS do commit (`@_on_commit`): sem notificação de algo que
# sofreu rollback, e uma falha aqui nunca derruba pagamento/pedido (o
# `robust=True` só loga). Todos são idempotentes via `dedupe_key`.
# ═══════════════════════════════════════════════════════════════════════════════

def _on_commit(fn):
    """Adia a execução do helper para o commit da transação corrente."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        transaction.on_commit(lambda: fn(*args, **kwargs), robust=True)
    return wrapper


def _notify_client_order(order_id: UUID, *, caller: str, notification_type: str, title: str, body: str, event: str) -> None:
    order = get_order_ref(order_id)
    if order is None:
        logger.warning("%s: pedido %s não encontrado.", caller, order_id)
        return
    notify(
        recipient_id=order.user_id_id,
        notification_type=notification_type,
        title=title,
        body=body.format(code=order.code),
        action_url=CLIENT_ORDERS_URL,
        target_type=TT.ORDER,
        target_id=order.order_id,
        dedupe_key=f"order:{order.order_id}:{event}",
    )


# =========================================================
# Pedidos (Order) — cliente
# =========================================================

@_on_commit
def notify_order_paid(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_paid", notification_type=NT.ORDER_PAID, event="paid",
        title="Pagamento confirmado", body="Seu pedido {code} foi confirmado.",
    )


@_on_commit
def notify_order_cancelled_no_stock(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_cancelled_no_stock", notification_type=NT.ORDER_CANCELLED, event="cancelled",
        title="Pedido cancelado",
        body="O pedido {code} foi cancelado por falta de estoque. O valor será estornado.",
    )


@_on_commit
def notify_order_expired(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_expired", notification_type=NT.ORDER_EXPIRED, event="expired",
        title="Pedido expirado", body="O pedido {code} expirou por falta de pagamento.",
    )


@_on_commit
def notify_order_refunded(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_refunded", notification_type=NT.ORDER_REFUNDED, event="refunded",
        title="Pedido reembolsado", body="O pedido {code} foi reembolsado.",
    )


@_on_commit
def notify_order_shipped(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_shipped", notification_type=NT.ORDER_SHIPPED, event="shipped",
        title="Pedido enviado", body="O pedido {code} saiu para entrega.",
    )


@_on_commit
def notify_order_in_transit(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_in_transit", notification_type=NT.ORDER_IN_TRANSIT, event="in_transit",
        title="Pedido em transporte", body="O pedido {code} está a caminho.",
    )


@_on_commit
def notify_order_delivered(order_id: UUID) -> None:
    _notify_client_order(
        order_id, caller="notify_order_delivered", notification_type=NT.ORDER_DELIVERED, event="delivered",
        title="Pedido entregue", body="O pedido {code} foi entregue. Esperamos que você goste!",
    )


@_on_commit
def notify_review_request(order_id: UUID) -> None:
    """Convite pra avaliar a compra (disparado por task, alguns dias após a entrega)."""
    _notify_client_order(
        order_id, caller="notify_review_request", notification_type=NT.REVIEW_REQUEST, event="review_request",
        title="Como foi sua compra?", body="Avalie os produtos do pedido {code} e ajude outros clientes.",
    )


# =========================================================
# Pedidos (Order) — admin
# =========================================================

@_on_commit
def notify_admins_new_order_paid(order_id: UUID) -> None:
    order = get_order_ref(order_id)
    if order is None:
        logger.warning("notify_admins_new_order_paid: pedido %s não encontrado.", order_id)
        return
    notify_admins(
        notification_type=NT.NEW_ORDER_PAID,
        title="Novo pedido pago",
        body=f"Pedido {order.code} aguardando envio.",
        action_url=ADMIN_ORDERS_URL,
        target_type=TT.ORDER,
        target_id=order.order_id,
        dedupe_key=f"order:{order.order_id}:paid:admin",
    )


# =========================================================
# Avaliações (Reviews)
# =========================================================

@_on_commit
def notify_review_pending_admins(reviews_id: UUID) -> None:
    """
    Avisa os admins que há avaliação para moderar. Chamada na criação e quando
    uma avaliação já publicada é editada (volta pra moderação). Mantém UMA
    pendência por avaliação: a anterior é removida e a nova nasce não lida.
    """
    from luxury_fashion.apps.reviews.selectors.reviews_selector import get_reviews_by_id

    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None:
        logger.warning("notify_review_pending_admins: avaliação %s não encontrada.", reviews_id)
        return
    if reviews.is_authorized:  # já moderada entre o commit e este momento
        return
    clear_target_notifications(target_type=TT.REVIEW, target_id=reviews_id, notification_type=NT.REVIEW_PENDING)
    notify_admins(
        notification_type=NT.REVIEW_PENDING,
        title="Avaliação aguardando moderação",
        body="Há uma nova avaliação para revisar.",
        action_url=ADMIN_REVIEWS_URL,
        actor_id=reviews.user_id_id,
        target_type=TT.REVIEW,
        target_id=reviews_id,
        dedupe_key=f"review:{reviews_id}:pending:{int(reviews.updated_at.timestamp())}",
    )


@_on_commit
def notify_review_published(reviews_id: UUID) -> None:
    """Avisa o cliente que a avaliação foi publicada e tira a pendência do sino dos admins."""
    from luxury_fashion.apps.reviews.selectors.reviews_selector import get_reviews_by_id

    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None or not reviews.is_authorized:
        return
    notify(
        recipient_id=reviews.user_id_id,
        notification_type=NT.REVIEW_PUBLISHED,
        title="Sua avaliação foi publicada",
        body="Obrigado por avaliar sua compra.",
        action_url=CLIENT_ORDERS_URL,
        target_type=TT.REVIEW,
        target_id=reviews_id,
        dedupe_key=f"review:{reviews_id}:published",
    )
    clear_target_notifications(target_type=TT.REVIEW, target_id=reviews_id, notification_type=NT.REVIEW_PENDING)


@_on_commit
def clear_review_pending(reviews_id: UUID) -> None:
    """Avaliação excluída: a pendência não pode ficar órfã no sino dos admins."""
    clear_target_notifications(target_type=TT.REVIEW, target_id=reviews_id, notification_type=NT.REVIEW_PENDING)


# ═══════════════════════════════════════════════════════════════════════════════
# Consumidor (endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

def list_notifications(
    recipient_id: UUID, *, page: int = 1, page_size: int = 20, unread_only: bool = False
) -> PageOut[NotificationOut]:
    qs = get_notifications_for_user(recipient_id, unread_only=unread_only)
    return paginate_queryset(qs, page, page_size, NotificationOut.from_orm)


def get_unread_count(recipient_id: UUID) -> UnreadCountOut:
    return UnreadCountOut(unread=count_unread(recipient_id))


def mark_notification_read(recipient_id: UUID, notification_id: UUID) -> NotificationOut:
    notification = get_notification_for_user(recipient_id, notification_id)
    if notification is None:
        raise NotificationNotFound()
    if not notification.is_read:
        mark_as_read(recipient_id=recipient_id, notification_id=notification_id)
        notification.refresh_from_db(fields=["read_at"])
    return NotificationOut.from_orm(notification)


def mark_all_notifications_read(recipient_id: UUID) -> MarkAllReadOut:
    return MarkAllReadOut(updated=mark_all_as_read(recipient_id=recipient_id))


def delete_own_notification(recipient_id: UUID, notification_id: UUID) -> None:
    if not delete_notification(recipient_id=recipient_id, notification_id=notification_id):
        raise NotificationNotFound()