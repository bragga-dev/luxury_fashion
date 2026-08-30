"""
ProductShipping Repository — persistência dos dados de frete (peso/dimensões)
de uma ProductVariant.
"""
from decimal import Decimal
from typing import Optional

from luxury_fashion.apps.products.models.product_shipping_model import ProductShipping
from luxury_fashion.apps.products.models.product_variant_model import ProductVariant


def create_shipping(
    variant_id: ProductVariant,
    weight: Decimal,
    height: Decimal,
    width: Decimal,
    length: Decimal,
    quantity: int = 1,
) -> ProductShipping:
    shipping = ProductShipping(
        variant_id=variant_id,
        weight=weight,
        height=height,
        width=width,
        length=length,
        quantity=quantity,
    )
    shipping.full_clean()
    shipping.save()
    return shipping


def update_shipping(shipping: ProductShipping, **fields) -> ProductShipping:
    for attr, value in fields.items():
        if value is not None:
            setattr(shipping, attr, value)
    shipping.full_clean()
    shipping.save()
    return shipping


def delete_shipping(shipping: ProductShipping) -> None:
    shipping.delete()


def get_or_create_shipping(variant_id: ProductVariant, **defaults) -> tuple[ProductShipping, bool]:
    """
    Útil no formulário de cadastro de variante: garante que sempre exista
    um registro de frete associado, mesmo que criado vazio/zerado a princípio.
    """
    shipping, created = ProductShipping.objects.get_or_create(
        variant_id=variant_id,
        defaults=defaults,
    )
    return shipping, created