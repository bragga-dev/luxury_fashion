import uuid
from typing import Optional

from ninja import Schema
from pydantic import field_validator

from luxury_fashion.apps.products.models.product_category_model import ProductCategory


class ProductCategoryCreateIn(Schema):
    category_name: str

    @field_validator("category_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v


class ProductCategoryUpdateIn(Schema):
    category_name: Optional[str] = None
    is_active: Optional[bool] = None


class ProductCategoryOut(Schema):
    product_category_id: uuid.UUID
    category_name: str
    category_image_url: str
    is_active: bool

    @classmethod
    def from_orm(cls, category: ProductCategory) -> "ProductCategoryOut":
        return cls(
            product_category_id=category.product_category_id,
            category_name=category.category_name,
            category_image_url=category.category_image_url,
            is_active=category.is_active,
        )


class ProductCategoryListOut(Schema):
    items: list[ProductCategoryOut]
