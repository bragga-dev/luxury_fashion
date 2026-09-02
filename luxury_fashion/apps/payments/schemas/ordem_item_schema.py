


import uuid
from datetime import datetime
from typing import Optional
from ninja import Schema, Field
from pydantic import field_validator
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant



class OrderItemOut(Schema):
    variant_id: uuid.UUID
    order_item_id: uuid.UUID
    order_item_quantity: int
    order_item_price: Decimal
    subtotal: Decimal  
    variant_name: Optional[str] = None  
    
    @classmethod
    def from_orm(cls, item: OrderItem) -> "OrderItemOut":
        return cls(
            variant_id=item.variant_id.variant_id,
            order_item_id=item.order_item_id,
            order_item_quantity=item.order_item_quantity,
            order_item_price=item.order_item_price,
            subtotal=item.subtotal(),
            variant_name=str(item.variant_id)  
        )

class OrderItemCreateIn(Schema):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0, le=100)  
    @field_validator('variant_id')
    def validate_variant_exists(cls, v):
        if not ProductVariant.objects.filter(variant_id=v).exists():
            raise ValueError("Variante não encontrada")
        return v


class OrderItemUpdateIn(Schema):
    quantity: Optional[int] = Field(None, gt=0)