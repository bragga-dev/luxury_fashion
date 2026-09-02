from uuid import UUID
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.cart.models.cart_model import Cart
from luxury_fashion.apps.cart.repositories.cart_item_repository import clear_cart
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

def get_cart_for_client(user_id: UUID) -> CartOut:
    get_or_create_cart_for_user(user_id=user_id)
    cart = get_cart_by_user_id(user_id=user_id)
    return CartOut.from_orm(cart)


def clear_cart_for_client(user_id: UUID) -> CartOut:
    cart = get_or_create_cart_for_user(user_id=user_id)
    clear_cart(cart)
    return get_cart_for_client(user_id=user_id)