import uuid
from typing import Optional

from ninja import Schema

from luxury_fashion.apps.products.models.product_image_model import ProductImage


class ImageUpdateIn(Schema):
    is_cover: Optional[bool] = None
    display_order: Optional[int] = None


class ImageOut(Schema):
    image_id: uuid.UUID
    product_image_url: str
    is_cover: bool
    display_order: int

    @classmethod
    def from_orm(cls, image: ProductImage) -> "ImageOut":
        try:
            url = image.product_image.url
        except Exception:
            url = ""
        return cls(
            image_id=image.image_id,
            product_image_url=url,
            is_cover=image.is_cover,
            display_order=image.display_order,
        )