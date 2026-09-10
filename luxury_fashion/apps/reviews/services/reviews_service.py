"""
Service layer de Reviews — avaliação de um item de pedido (`OrderItem`)
comprado pelo cliente, e do agregado derivado (média de avaliações por
produto).

Fluxo:
- Cliente avalia um `OrderItem` do próprio pedido, já COMPLETED (uma vez
  só, 1:1 com o item — reforçado pelo `OneToOneField` no model).
  `user_id` nunca é confiado do payload — sempre resolvido de
  `request.auth` no service.
- Toda avaliação nasce com `is_authorized=False`; só entra na média
  pública do produto depois que um admin autoriza.
- Qualquer criação/edição/autorização/revogação/exclusão de uma avaliação
  recalcula a média do produto envolvido.
"""
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Avg, Count

from luxury_fashion.apps.core.exceptions import OrderNotFound
from luxury_fashion.apps.core.exceptions.service_exception import (
    AverageRatingAlreadyExists,
    AverageRatingNotFound,
    OrderItemNotReviewable,
)

from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.selectors.order_selector import (
    get_order_item_by_id,
    get_order_item_by_variant,
)

from luxury_fashion.apps.reviews.models.reviews_model import Reviews
from luxury_fashion.apps.reviews.repositories.reviews_repository import (
    authorize_reviews,
    create_reviews,
    delete_reviews,
    revoke_rating_authorization,
    update_reviews,
)
from luxury_fashion.apps.reviews.selectors.reviews_selector import (
    get_authorized_reviews,
    get_pending_authorization_reviews,
    get_reviews_by_id,
    get_reviews_by_order_item,
    get_reviews_by_user,
    validate_user_already_rated_order_item,
)
from luxury_fashion.apps.reviews.schemas.reviews_schema import (
    ReviewsCreateIn,
    ReviewsOut,
    ReviewsPrivateOut,
    ReviewsUpdateIn,
)


@transaction.atomic
def recalculate_product_average_rating(product_id: UUID) -> dict:
    """
    Recalcula a média de avaliações de um produto específico (através de
    todos os `OrderItem` de suas variantes). Retorna média e total.
    """
    order_item_ids = get_order_item_by_variant(product_id=product_id)

    stats = Reviews.objects.filter(order_item_id__in=order_item_ids, is_authorized=True).aggregate(
        avg_rating=Avg("reviews"), total_reviews=Count("reviews_id")
    )

    average_rating = (
        round(Decimal(str(stats["avg_rating"])), 1) if stats["avg_rating"] is not None else Decimal("0.0")
    )
    total_reviews = stats["total_reviews"] or 0

    return {"product_id": product_id, "average_rating": average_rating, "total_reviews": total_reviews}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _get_own_review(user_id: UUID, reviews_id: UUID) -> Reviews:
    """Busca a avaliação garantindo que pertence ao cliente autenticado."""
    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None or reviews.user_id_id != user_id:
        raise AverageRatingNotFound()
    return reviews


def _refresh_aggregates(reviews: Reviews) -> None:
    """Recalcula o agregado do produto ligado à avaliação."""
    product_id = reviews.order_item_id.variant_id.product_id_id
    recalculate_product_average_rating(product_id=product_id)


def _get_reviewable_order_item(user_id: UUID, order_item_id: UUID):
    """
    Busca o `OrderItem` garantindo que pertence ao cliente autenticado e
    que o pedido já está concluído — únicas condições pra poder avaliar.
    """
    order_item = get_order_item_by_id(order_item_id=order_item_id)
    if order_item is None or order_item.order_id.user_id_id != user_id:
        raise OrderNotFound()
    if order_item.order_id.order_status != Order.StatusOrder.COMPLETED:
        raise OrderItemNotReviewable()
    return order_item


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def create_review_for_client(user_id: UUID, data: ReviewsCreateIn) -> ReviewsPrivateOut:
    """Cliente avalia um item do próprio pedido concluído."""
    order_item = _get_reviewable_order_item(user_id=user_id, order_item_id=data.order_item_id)

    if validate_user_already_rated_order_item(user_id=user_id, order_item_id=order_item.order_item_id):
        raise AverageRatingAlreadyExists()

    reviews = create_reviews(
        user=order_item.order_id.user_id,
        order_item=order_item,
        reviews=data.reviews,
        comment=data.comment,
    )

    _refresh_aggregates(reviews)
    return ReviewsPrivateOut.from_orm(reviews)


def list_my_reviews(user_id: UUID) -> list[ReviewsPrivateOut]:
    """Lista todas as avaliações do cliente autenticado (autorizadas ou não)."""
    return [ReviewsPrivateOut.from_orm(reviews) for reviews in get_reviews_by_user(user_id=user_id)]


def get_own_review_detail(user_id: UUID, reviews_id: UUID) -> ReviewsPrivateOut:
    reviews = _get_own_review(user_id=user_id, reviews_id=reviews_id)
    return ReviewsPrivateOut.from_orm(reviews)


@transaction.atomic
def update_own_review(user_id: UUID, reviews_id: UUID, data: ReviewsUpdateIn) -> ReviewsPrivateOut:
    """
    Cliente edita a própria nota/comentário.

    Se a avaliação já estava autorizada (pública) e o conteúdo muda, ela
    volta para moderação (`is_authorized=False`) — precisa passar pelo
    admin de novo antes de voltar a aparecer publicamente.
    """
    reviews = _get_own_review(user_id=user_id, reviews_id=reviews_id)

    fields = data.model_dump(exclude_unset=True)
    content_changed = bool(fields)

    reviews = update_reviews(reviews, **fields)

    if content_changed and reviews.is_authorized:
        reviews = revoke_rating_authorization(reviews=reviews)

    _refresh_aggregates(reviews)
    return ReviewsPrivateOut.from_orm(reviews)


@transaction.atomic
def delete_own_review(user_id: UUID, reviews_id: UUID) -> None:
    """Cliente exclui a própria avaliação."""
    reviews = _get_own_review(user_id=user_id, reviews_id=reviews_id)
    product_id = reviews.order_item_id.variant_id.product_id_id

    delete_reviews(reviews)

    recalculate_product_average_rating(product_id=product_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Público (visitantes — leitura)
# ═══════════════════════════════════════════════════════════════════════════════

def list_public_reviews_for_order_item(order_item_id: UUID) -> list[ReviewsOut]:
    """Lista a avaliação autorizada de um item de pedido específico, se houver."""
    reviews = get_reviews_by_order_item(order_item_id=order_item_id)
    if reviews is None or not reviews.is_authorized:
        return []
    return [ReviewsOut.from_orm(reviews)]


def list_public_reviews_for_product(product_id: UUID) -> list[ReviewsOut]:
    """Lista as avaliações autorizadas de todos os itens de um produto."""
    order_item_ids = get_order_item_by_variant(product_id=product_id)
    reviews = Reviews.objects.filter(order_item_id__in=order_item_ids, is_authorized=True).order_by("-created_at")
    return [ReviewsOut.from_orm(r) for r in reviews]


def get_product_rating_summary(product_id: UUID) -> dict:
    """Média/total de avaliações autorizadas de um produto. Zerado se ainda não tem avaliações."""
    return recalculate_product_average_rating(product_id=product_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

def list_pending_reviews_admin() -> list[ReviewsPrivateOut]:
    """Avaliações ainda não autorizadas, aguardando moderação."""
    return [ReviewsPrivateOut.from_orm(reviews) for reviews in get_pending_authorization_reviews()]


def list_authorized_reviews_admin() -> list[ReviewsPrivateOut]:
    return [ReviewsPrivateOut.from_orm(reviews) for reviews in get_authorized_reviews()]


@transaction.atomic
def authorize_review_admin(reviews_id: UUID) -> ReviewsPrivateOut:
    """Admin autoriza a exibição pública de uma avaliação."""
    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None:
        raise AverageRatingNotFound()

    reviews = authorize_reviews(reviews=reviews)
    _refresh_aggregates(reviews=reviews)
    return ReviewsPrivateOut.from_orm(reviews)


@transaction.atomic
def revoke_review_admin(reviews_id: UUID) -> ReviewsPrivateOut:
    """Admin revoga a autorização (ex: comentário ofensivo denunciado)."""
    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None:
        raise AverageRatingNotFound()

    reviews = revoke_rating_authorization(reviews=reviews)
    _refresh_aggregates(reviews=reviews)
    return ReviewsPrivateOut.from_orm(reviews)


@transaction.atomic
def delete_review_admin(reviews_id: UUID) -> None:
    """Admin exclui permanentemente uma avaliação."""
    reviews = get_reviews_by_id(reviews_id=reviews_id)
    if reviews is None:
        raise AverageRatingNotFound()

    product_id = reviews.order_item_id.variant_id.product_id_id
    delete_reviews(reviews=reviews)
    recalculate_product_average_rating(product_id=product_id)