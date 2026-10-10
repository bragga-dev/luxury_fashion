from uuid import UUID
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.cart.repositories.cart_item_repository import clear_cart, update_item_unit_price
from luxury_fashion.apps.cart.repositories.cart_repository import create_cart
from luxury_fashion.apps.cart.schemas.cart_schema import CartOut
from luxury_fashion.apps.cart.selectors.cart_selector import get_cart_by_user_id
from luxury_fashion.apps.accounts.selectors.user_selector import get_user_by_id
from luxury_fashion.apps.core.exceptions.user import UserNotFound


def get_or_create_cart_for_user(user_id: UUID) -> Cart:
    cart = get_cart_by_user_id(user_id=user_id)
    if cart is not None:
        return cart

    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    return create_cart(user)

def refresh_cart_prices(user_id: UUID) -> bool:
    """
    Ressincroniza o preço dos itens com o preço ATUAL da variante.
    `unit_price_item` é gravado só na criação do item, então sem isso o
    carrinho continua cobrando o preço antigo. Devolve True se algum preço
    mudou (os totais são recalculados e o frete escolhido é invalidado).
    """
    cart = get_cart_by_user_id(user_id=user_id)
    if cart is None:
        return False

    changed = False
    for item in cart.items.all():
        current_price = item.variant_id.price
        if item.unit_price_item != current_price:
            update_item_unit_price(item=item, unit_price=current_price)
            changed = True
    if changed:
        cart.update_totals()
    return changed


def get_cart_for_client(user_id: UUID) -> CartOut:
    get_or_create_cart_for_user(user_id=user_id)
    refresh_cart_prices(user_id=user_id)
    cart = get_cart_by_user_id(user_id=user_id)
    return CartOut.from_orm(cart)


def clear_cart_for_client(user_id: UUID) -> CartOut:
    cart = get_or_create_cart_for_user(user_id=user_id)
    clear_cart(cart)
    return get_cart_for_client(user_id=user_id)