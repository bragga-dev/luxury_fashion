"""SKU opcional e único na variante."""
from decimal import Decimal

import pytest

from luxury_fashion.apps.core.exceptions import VariantAlreadyExists
from luxury_fashion.apps.products.schemas.product_variant_schema import VariantCreateIn, VariantOut, VariantUpdateIn
from luxury_fashion.apps.products.services.product_variant_service import (
    create_variant_for_admin,
    update_variant_for_admin,
)

pytestmark = pytest.mark.django_db


def _payload(**kw):
    base = dict(size="GG", color="white", price=Decimal("50.00"), stock=1)
    base.update(kw)
    return VariantCreateIn(**base)


def test_cria_variante_sem_sku(product):
    out = create_variant_for_admin(product.product_id, _payload())
    assert out.sku is None


def test_sku_vazio_vira_none_e_nao_colide(product):
    a = create_variant_for_admin(product.product_id, _payload(sku="  "))
    b = create_variant_for_admin(product.product_id, _payload(size="XGG", sku=""))
    assert a.sku is None and b.sku is None


def test_sku_duplicado_da_conflito(product, variant):
    with pytest.raises(VariantAlreadyExists):
        create_variant_for_admin(product.product_id, _payload(sku=variant.sku))


def test_update_para_sku_de_outra_variante_da_conflito(variant, other_variant):
    with pytest.raises(VariantAlreadyExists):
        update_variant_for_admin(other_variant.variant_id, VariantUpdateIn(sku=variant.sku))


def test_variant_out_aceita_sku_nulo(variant):
    variant.sku = None
    variant.save()
    assert VariantOut.from_orm(variant).sku is None