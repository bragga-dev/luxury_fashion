
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from ninja import Schema, Fiel
from __future__ import annotations

from pydantic import field_validator


from luxury_fashion.apps.reviews.models.reviews_model import Reviews
from luxury_fashion.apps.payments.schemas.order_item_schema import OrderItemOut
from luxury_fashion.apps.accounts.schemas.user_schema import UserOut



MAX_COMMENT_LENGTH = 500


class ReviewsEnum(int, Enum):
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5

    @classmethod
    def get_display_name(cls, value: int) -> str:
        choices_dict = dict(ReviewsEnum.ReviewsChoices.choices)
        return choices_dict.get(value, str(value))


def _validate_comment(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if len(v) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Comentário não pode exceder {MAX_COMMENT_LENGTH} caracteres.")
    return v


class ReviewsOut(Schema):
    reviews_id: UUID
    order_item: OrderItemOut
    user: UserOut
    reviews: ReviewsEnum
    reviews_label: str
    comment: str
    created_at: datetime

    @classmethod
    def from_orm(cls, reviews: Reviews) -> "ReviewsOut":
        return cls(
            reviews_id=reviews.reviews_id,
            order_item=OrderItemOut.from_orm(reviews.order_item),
            user=UserOut.from_orm(reviews.user),
            reviews=reviews.reviews,
            reviews_label=reviews.get_reviews_display(),
            comment=reviews.comment,
            created_at=reviews.created_at,
        )

class ReviewsPrivateOut(Schema):
    reviews_id: UUID
    order_item: OrderItemOut
    user: UserOut
    reviews: ReviewsEnum
    reviews_label: str
    comment: str
    created_at: datetime
    updated_at: datetime
    is_authorized: bool

    @classmethod
    def from_orm(cls, reviews: Reviews) -> "ReviewsOut":
        return cls(
            reviews_id=reviews.reviews_id,
            order_item=OrderItemOut.from_orm(reviews.order_item),
            user=UserOut.from_orm(reviews.user),
            reviews=reviews.reviews,
            reviews_label=reviews.get_reviews_display(),
            comment=reviews.comment,
            created_at=reviews.created_at,
            updated_at=reviews.updated_at,
            is_authorized=reviews.is_authorized,
        )

class ReviewsCreateIn(Schema):
    order_item_id: UUID
    user_id: UUID
    reviews: ReviewsEnum
    comment: Optional[str] = None

    @field_validator("comment")
    @classmethod
    def validate_comment_create(cls, v: Optional[str]) -> Optional[str]:
        return _validate_comment(v)




class ReviewsFilter(Schema):
    order_item_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    reviews: Optional[ReviewsEnum] = None
    is_authorized: Optional[bool] = None


class ReviewsList(Schema):
    items: list[ReviewsOut]


class ReviewsPrivateList(Schema):
    items: list[ReviewsPrivateOut]