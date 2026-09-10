from typing import Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from luxury_fashion.apps.reviews.models.reviews_model import Reviews


DEFAULT_RELATED = ("user_id", "order_item_id", "order_item_id__order_id")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_id(reviews_id: UUID) -> Optional[Reviews]:
    """Retorna a avaliação pelo ID, ou None se não existir."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(reviews_id=reviews_id).first()


def get_reviews_by_order_item(order_item_id: UUID) -> Optional[Reviews]:
    """Retorna a avaliação vinculada a um item do pedido."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(order_item_id=order_item_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Item do Pedido
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_product(order_item_id: UUID, authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna as avaliações de um item de pedido específico."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).filter(order_item_id=order_item_id)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Usuário
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_user(user_id: UUID) -> QuerySet[Reviews]:
    """Retorna todas as avaliações feitas por um usuário específico."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(user_id=user_id).order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Nota
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_stars(rating: int, authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna as avaliações com uma nota específica (1 a 5 estrelas)."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).filter(reviews=rating)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Autorização
# ═══════════════════════════════════════════════════════════════════════════════

def get_pending_authorization_reviews() -> QuerySet[Reviews]:
    """Retorna as avaliações ainda não autorizadas (aguardando moderação)."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=False).order_by("-created_at")


def get_authorized_reviews() -> QuerySet[Reviews]:
    """Retorna apenas as avaliações já autorizadas (públicas)."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=True).order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem com Comentário
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_with_comment(authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna avaliações que possuem comentário preenchido."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).exclude(comment__isnull=True).exclude(comment="")
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_reviews(
    user_id: Optional[UUID] = None,
    order_id: Optional[UUID] = None,
    order_item_id: Optional[UUID] = None,
    rating: Optional[int] = None,
    is_authorized: Optional[bool] = None,
    has_comment: Optional[bool] = None,
) -> QuerySet[Reviews]:
    """
    Listagem administrativa de avaliações com filtros combináveis.
    Nenhum filtro informado retorna tudo.
    """
    q = Q()

    if user_id:
        q &= Q(user_id=user_id)
    if order_id:
        q &= Q(order_item_id__order_id=order_id)
    if order_item_id:
        q &= Q(order_item_id=order_item_id)
    if rating is not None:
        q &= Q(reviews=rating)
    if is_authorized is not None:
        q &= Q(is_authorized=is_authorized)
    if has_comment is not None:
        if has_comment:
            q &= Q(comment__isnull=False) & ~Q(comment="")
        else:
            q &= Q(Q(comment__isnull=True) | Q(comment=""))

    qs = Reviews.objects.select_related(*DEFAULT_RELATED)
    qs = qs.filter(q) if q else qs.all()
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_reviews_exists(reviews_id: UUID) -> bool:
    """Verifica se uma avaliação existe."""
    return Reviews.objects.filter(reviews_id=reviews_id).exists()


def validate_order_item_already_rated(order_item_id: UUID) -> bool:
    """Verifica se um item do pedido já possui avaliação."""
    return Reviews.objects.filter(order_item_id=order_item_id).exists()


def validate_user_already_rated_order_item(user_id: UUID, order_item_id: UUID) -> bool:
    """Verifica se um usuário já avaliou um item específico do pedido."""
    return Reviews.objects.filter(user_id=user_id, order_item_id=order_item_id).exists()