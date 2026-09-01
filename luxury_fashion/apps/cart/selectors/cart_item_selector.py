"""
CartItem Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
from uuid import UUID
from typing import Optional

from django.db.models import QuerySet

from luxury_fashion.apps.cart.models.cart_item_model import CartItem


def get_item_by_id(cart_item_id: UUID) -> Optional[CartItem]:
    return (CartItem.objects.select_related("variant_id__product_id", "cart_id").filter(cart_item_id=cart_item_id).first())


def get_item_by_id_and_cart(cart_item_id: UUID, cart_id: UUID) -> Optional[CartItem]:
    return (CartItem.objects.select_related("variant_id__product_id").filter(cart_item_id=cart_item_id, cart_id=cart_id).first())


def get_item_by_variant(cart_id:UUID, variant_id:UUID) -> Optional[CartItem]:
    return CartItem.objects.filter(cart_id=cart_id, variant_id=variant_id).first()


def get_items_by_cart(cart_id: UUID) -> QuerySet[CartItem]:
    return CartItem.objects.filter(cart_id=cart_id).select_related("variant_id__product_id")