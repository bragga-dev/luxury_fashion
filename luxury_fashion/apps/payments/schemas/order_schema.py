import uuid
from datetime import datetime
from typing import Optional
from ninja import Schema, Field
from pydantic import field_validator
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from typing import List, Optional
from luxury_fashion.apps.payments.schemas.ordem_item_schema import OrderItemOut
from enum import Enum
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.accounts.models.user_model import User



class StatusOrderEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"
    

class OrderOut(Schema):
    user_id: uuid.UUID
    cart_id: Optional[uuid.UUID] = None
    order_id: uuid.UUID
    code: str
    order_status: StatusOrderEnum
    total_geral: Decimal
    subtotal: Decimal
    order_shipping_total: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut] = Field(default_factory=list)
    payment_status: Optional[str] = None

    @classmethod
    def from_orm(cls, order: Order) -> "OrderOut":
        items = [OrderItemOut.from_orm(item) for item in order.items.all()]
        
        return cls(
            user_id=order.user_id.user_id,  
            cart_id=order.cart_id.cart_id,  
            order_id=order.order_id,
            code=order.code,
            order_status=order.order_status,
            total_geral=order.total_geral,  
            subtotal=order.subtotal,
            order_shipping_total=order.order_shipping_total,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=items
        )

class OrderCreateIn(Schema):
    user_id: uuid.UUID
    cart_id: uuid.UUID  
    payment_method: str  
    
    @field_validator('user_id')
    def validate_user_exists(cls, v):
        if not User.objects.filter(user_id=v).exists():
            raise ValueError("Usuário não encontrado")
        return v
    
    @field_validator('cart_id')
    def validate_cart(cls, v):
        if not Cart.objects.filter(cart_id=v).exists():
            raise ValueError("Carrinho não encontrado")
        return v

    @field_validator('payment_method')
    def validate_payment_method(cls, v):
        valid_methods = ['PIX', 'BOLETO', 'CREDIT_CARD']
        if v not in valid_methods:
            raise ValueError(f"Forma de pagamento inválida. Use: {', '.join(valid_methods)}")
        return v


    @field_validator('cart_id')
    def validate_cart_belongs_to_user(cls, v, info):
        cart = Cart.objects.filter(cart_id=v).first()
        if not cart:
            raise ValueError("Carrinho não encontrado")
        if cart.user_id.user_id != info.data.get('user_id'):
            raise ValueError("Carrinho não pertence ao usuário")
        return v