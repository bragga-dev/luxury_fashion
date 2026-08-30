"""
ProductVariant Repository — persistência de ProductVariant.
"""
from decimal import Decimal
from typing import Optional

from luxury_fashion.apps.products.models.product_model import Product
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def create_variant(
    product_id: Product,
    price: Decimal,
    size: Optional[str] = None,
    color: Optional[str] = None,
    gender: Optional[str] = None,
    stock: int = 0,
    description: str = "",
) -> ProductVariant:
    variant = ProductVariant(
        product_id=product_id,
        size=size,
        color=color,
        gender=gender,
        price=price,
        stock=stock,
        description=description,
    )
    variant.full_clean()
    variant.save()
    return variant


def update_variant(variant: ProductVariant, **fields) -> ProductVariant:
    for attr, value in fields.items():
        if value is not None:
            setattr(variant, attr, value)
    variant.full_clean()
    variant.save()
    return variant


def delete_variant(variant: ProductVariant) -> None:
    variant.delete()


def activate_variant(variant: ProductVariant) -> ProductVariant:
    if not variant.is_active:
        variant.is_active = True
        variant.save(update_fields=["is_active"])
    return variant


def deactivate_variant(variant: ProductVariant) -> ProductVariant:
    if variant.is_active:
        variant.is_active = False
        variant.save(update_fields=["is_active"])
    return variant


def adjust_variant_stock(variant: ProductVariant, delta: int) -> ProductVariant:
    """
    Ajusta o estoque em `delta` (positivo repõe, negativo baixa — ex.: venda).
    """
    new_stock = variant.stock + delta
    if new_stock < 0:
        raise ValueError("Estoque insuficiente para essa operação.")
    variant.stock = new_stock
    variant.full_clean()
    variant.save(update_fields=["stock"])
    return variant


def set_variant_stock(variant: ProductVariant, stock: int) -> ProductVariant:
    variant.stock = stock
    variant.full_clean()
    variant.save(update_fields=["stock"])
    return variant