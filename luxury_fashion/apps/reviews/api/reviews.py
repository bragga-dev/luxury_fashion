"""
Review endpoints — avaliação de itens de pedido (`OrderItem`) pelo cliente
que comprou, leitura pública por produto/item, e moderação por admin.
"""
import uuid

from ninja import Router, Status
from django_ratelimit.decorators import ratelimit

from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.core.exceptions import OrderNotFound
from luxury_fashion.apps.core.exceptions.service_exception import (
    AverageRatingAlreadyExists,
    AverageRatingNotFound,
    OrderItemNotReviewable,
)
from luxury_fashion.apps.core.permissions.auth_classes import AdminOnlyAuth, ClientOnlyAuth
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.reviews.schemas.reviews_schema import (
    ProductRatingSummaryOut,
    ReviewsCreateIn,
    ReviewsOut,
    ReviewsPrivateOut,
    ReviewsUpdateIn,
)
from luxury_fashion.apps.reviews.services.reviews_service import (
    authorize_review_admin,
    create_review_for_client,
    delete_own_review,
    delete_review_admin,
    get_own_review_detail,
    get_product_rating_summary,
    list_authorized_reviews_admin,
    list_my_reviews,
    list_pending_reviews_admin,
    list_public_reviews_for_order_item,
    list_public_reviews_for_product,
    revoke_review_admin,
    update_own_review,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente — avalia itens dos próprios pedidos concluídos
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response={201: ReviewsPrivateOut, 404: MessageOut, 409: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cria uma avaliação para um item de pedido concluído do próprio cliente",
)
@ratelimit(key="user", rate="20/m", block=True)
def create_review_router(request, payload: ReviewsCreateIn):
    try:
        user: User = request.auth
        return Status(201, create_review_for_client(user.user_id, payload))
    except OrderNotFound as e:
        return Status(404, {"detail": str(e)})
    except (OrderItemNotReviewable, AverageRatingAlreadyExists) as e:
        return Status(409, {"detail": str(e)})


@router.get(
    "/me",
    response={200: list[ReviewsPrivateOut]},
    auth=ClientOnlyAuth(),
    summary="Lista as avaliações do cliente autenticado (autorizadas ou não)",
)
@ratelimit(key="user", rate="60/m", block=True)
def list_my_reviews_router(request):
    user: User = request.auth
    return Status(200, list_my_reviews(user.user_id))


@router.get(
    "/me/{reviews_id}",
    response={200: ReviewsPrivateOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Detalha uma avaliação do próprio cliente",
)
@ratelimit(key="user", rate="60/m", block=True)
def get_my_review_router(request, reviews_id: uuid.UUID):
    try:
        user: User = request.auth
        return Status(200, get_own_review_detail(user.user_id, reviews_id))
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})


@router.patch(
    "/me/{reviews_id}",
    response={200: ReviewsPrivateOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Edita a nota/comentário da própria avaliação (volta pra moderação se já estava pública)",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_my_review_router(request, reviews_id: uuid.UUID, payload: ReviewsUpdateIn):
    try:
        user: User = request.auth
        return Status(200, update_own_review(user.user_id, reviews_id, payload))
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})


@router.delete(
    "/me/{reviews_id}",
    response={204: None, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Exclui a própria avaliação",
)
@ratelimit(key="user", rate="20/m", block=True)
def delete_my_review_router(request, reviews_id: uuid.UUID):
    try:
        user: User = request.auth
        delete_own_review(user.user_id, reviews_id)
        return Status(204, None)
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# Público — leitura, sem autenticação
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/products/{product_id}",
    response={200: list[ReviewsOut]},
    auth=None,
    summary="Lista as avaliações autorizadas (públicas) de um produto",
)
def list_product_reviews_router(request, product_id: uuid.UUID):
    return Status(200, list_public_reviews_for_product(product_id))


@router.get(
    "/products/{product_id}/summary",
    response={200: ProductRatingSummaryOut},
    auth=None,
    summary="Média e total de avaliações autorizadas de um produto",
)
def get_product_rating_summary_router(request, product_id: uuid.UUID):
    return Status(200, get_product_rating_summary(product_id))


@router.get(
    "/order-items/{order_item_id}",
    response={200: list[ReviewsOut]},
    auth=None,
    summary="Avaliação pública (se houver e estiver autorizada) de um item de pedido específico",
)
def list_order_item_reviews_router(request, order_item_id: uuid.UUID):
    return Status(200, list_public_reviews_for_order_item(order_item_id))


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — moderação
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/admin/pending",
    response={200: list[ReviewsPrivateOut]},
    auth=AdminOnlyAuth(),
    summary="[Admin] Lista avaliações aguardando moderação",
)
def list_pending_reviews_router(request):
    return Status(200, list_pending_reviews_admin())


@router.get(
    "/admin/authorized",
    response={200: list[ReviewsPrivateOut]},
    auth=AdminOnlyAuth(),
    summary="[Admin] Lista avaliações já autorizadas",
)
def list_authorized_reviews_router(request):
    return Status(200, list_authorized_reviews_admin())


@router.post(
    "/admin/{reviews_id}/authorize",
    response={200: ReviewsPrivateOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Autoriza a exibição pública de uma avaliação",
)
def authorize_review_router(request, reviews_id: uuid.UUID):
    try:
        return Status(200, authorize_review_admin(reviews_id))
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})


@router.post(
    "/admin/{reviews_id}/revoke",
    response={200: ReviewsPrivateOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Revoga a autorização pública de uma avaliação",
)
def revoke_review_router(request, reviews_id: uuid.UUID):
    try:
        return Status(200, revoke_review_admin(reviews_id))
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})


@router.delete(
    "/admin/{reviews_id}",
    response={204: None, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="[Admin] Exclui permanentemente uma avaliação",
)
def delete_review_admin_router(request, reviews_id: uuid.UUID):
    try:
        delete_review_admin(reviews_id)
        return Status(204, None)
    except AverageRatingNotFound as e:
        return Status(404, {"detail": str(e)})