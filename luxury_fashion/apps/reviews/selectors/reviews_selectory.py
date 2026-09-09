
from typing import Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from luxury_fashion.apps.reviews.models.reviews_model  import Reviews


DEFAULT_RELATED = ("user_id", "order_item_id", "order_item_id__order_id")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_id(reviews_id: UUID) -> Optional[Reviews]:
    """Retorna a avaliação pelo ID, ou None se não existir."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(reviews_id=reviews_id).first()


def get_reviews_by_order_item(order_item_id: UUID) -> Optional[Reviews]:
    """Retorna a avaliação vinculada a um produto"""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(order_item_id=order_item_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Produto
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_product(order_item_id: UUID, authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna as avaliações de um produto específico."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).filter(order_item_id=order_item_id)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-order_item_id", "-created_at")



# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Cliente
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_user(user_id: UUID) -> QuerySet[Reviews]:
    """Retorna todas as avaliações feitas por um usuário específico."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(user_id=user_id).order_by("-reviews", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Nota
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_by_stars(reviews: int, authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna as avaliações com uma nota específica (1 a 5 estrelas)."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).filter(reviews=reviews)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Autorização
# ═══════════════════════════════════════════════════════════════════════════════

def get_pending_authorization_reviews() -> QuerySet[Reviews]:
    """Retorna as avaliações ainda não autorizadas (aguardando moderação)."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=False).order_by("-reviews", "-created_at")


def get_authorized_reviews() -> QuerySet[Reviews]:
    """Retorna apenas as avaliações já autorizadas (públicas)."""
    return Reviews.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=True).order_by("-reviews", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem com Comentário
# ═══════════════════════════════════════════════════════════════════════════════

def get_reviews_with_comment(authorized_only: bool = True) -> QuerySet[Reviews]:
    """Retorna avaliações que possuem comentário preenchido."""
    qs = Reviews.objects.select_related(*DEFAULT_RELATED).exclude(comment__isnull=True).exclude(comment="")
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-reviews", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_average_reviews(
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    rating: Optional[int] = None,
    is_authorized: Optional[bool] = None,
) -> QuerySet[Reviews]:
    """
    Listagem administrativa de avaliações com filtros combináveis.
    Nenhum filtro informado retorna tudo.
    """
    q = Q()

    if service_id:
        q &= Q(service_id=service_id)
    if employee_id:
        q &= Q(employee_id=employee_id)
    if client_id:
        q &= Q(client_id=client_id)
    if rating is not None:
        q &= Q(rating=rating)
    if is_authorized is not None:
        q &= Q(is_authorized=is_authorized)

    qs = Reviews.objects.select_related(*DEFAULT_RELATED).filter(q) if q else Reviews.objects.select_related(*DEFAULT_RELATED).all()
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_average_reviews_exists(rating_id: UUID) -> bool:
    """Verifica se uma avaliação existe."""
    return Reviews.objects.filter(id=rating_id).exists()


def validate_product_already_rated(scheduling_id: UUID) -> bool:
    """Verifica se um produto já possui avaliação ."""
    return Reviews.objects.filter(scheduling_id=scheduling_id).exists()


