"""
Repository de AverageRating — funções de persistência (criação,
atualização, autorização e exclusão) da avaliação real deixada pelo
cliente sobre um atendimento concluído.

Como no repository de Service, essas funções recebem valores já resolvidos
(instâncias de model, não IDs) — resolver `scheduling_id`/`service_id`/
`employee_id`/`client_id` pra instância é responsabilidade da camada de
`services.py`, não daqui.
"""
from typing import Optional

from django.db import transaction


from luxury_fashion.apps.reviews.models.reviews_model import Reviews
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.payments.models.order_item_model import OrderItem


REVIEWS_FIELDS = {"comment", "reviews"}


@transaction.atomic
def create_reviews(*, user: User, order_item: OrderItem, reviews: int, comment: Optional[str] = None) -> Reviews:
    reviews = Reviews(
        user_id=user,
        order_item_id=order_item,
        reviews=reviews,
        comment=comment,
    )
    reviews.save()
    return reviews


@transaction.atomic
def update_reviews(instance: Reviews, **fields) -> Reviews:
    """
    `instance` (não `reviews`) de propósito: o campo de nota do model se
    chama `reviews`, então um parâmetro com esse mesmo nome colide com a
    chave `"reviews"` vinda de `**fields` (`TypeError: multiple values`).
    """
    unknown = set(fields) - REVIEWS_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis na Avaliação: {', '.join(sorted(unknown))}")

    if not fields:
        return instance

    for field, value in fields.items():
        setattr(instance, field, value)

    instance.save()
    return instance


@transaction.atomic
def authorize_reviews(reviews: Reviews) -> Reviews:
    """Autoriza a exibição pública da avaliação (ex: moderação aprovou)."""
    reviews.is_authorized = True
    reviews.save(update_fields=["is_authorized", "updated_at"])
    return reviews


@transaction.atomic
def revoke_rating_authorization(reviews: Reviews) -> Reviews:
    """Revoga a autorização de exibição pública da avaliação."""
    reviews.is_authorized = False
    reviews.save(update_fields=["is_authorized", "updated_at"])
    return reviews


@transaction.atomic
def delete_reviews(reviews: Reviews) -> None:
    """Exclui a avaliação permanentemente do banco."""
    reviews.delete()