






from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.cart.models.cart_model import Cart


def get_or_create_cart(user_id: User) -> Cart:
    cart, _ = Cart.objects.get_or_create(user_id=user_id)
    return cart