"""
Product Repository — persistência de Product.

Este módulo só deve conter acesso a dados (criar/ler/atualizar/excluir no
banco). Qualquer decisão sobre *quais* campos aplicar, *se* uma transição de
estado é permitida, mensagens de erro de domínio etc. é regra de negócio e
pertence ao service.
"""
from luxury_fashion.apps.products.models.product_category_model import ProductCategory
from luxury_fashion.apps.products.models.product_model import Product


def create_product(
    product_name: str,
    product_category_id: ProductCategory,
    is_active: bool = True,
) -> Product:
    product = Product(
        product_name=product_name,
        product_category_id=product_category_id,
        is_active=is_active,
    )
    product.full_clean()
    product.save()
    return product


def update_product(product: Product, **fields) -> Product:
    """
    Aplica no model exatamente os campos recebidos. A decisão de quais
    campos entram aqui (ex.: só os explicitamente enviados, se `None` deve
    ou não limpar um campo, etc.) é responsabilidade do service — o
    repository apenas persiste o que já chegou pronto.
    """
    for attr, value in fields.items():
        setattr(product, attr, value)
    product.full_clean()
    product.save()
    return product


def delete_product(product: Product) -> None:
    product.delete()


def activate_product(product: Product) -> Product:
    product.is_active = True
    product.save(update_fields=["is_active"])
    return product


def deactivate_product(product: Product) -> Product:
    product.is_active = False
    product.save(update_fields=["is_active"])
    return product