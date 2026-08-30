"""
ProductShipping Selectors — queries de leitura. Nenhuma escrita acontece aqui.
"""
import uuid
from typing import Optional

from luxury_fashion.apps.products.models.product_shipping_model import ProductShipping


def get_shipping_by_variant(variant_id: uuid.UUID) -> Optional[ProductShipping]:
    return ProductShipping.objects.select_related("variant_id").filter(variant_id=variant_id).first()


def shipping_exists_for_variant(variant_id: uuid.UUID) -> bool:
    return ProductShipping.objects.filter(variant_id=variant_id).exists()