from luxury_fashion.apps.core.exceptions.auth import InvalidCredentials, InvalidPassword, InvalidToken, InvalidGoogleToken, SessionNotFound
from luxury_fashion.apps.core.exceptions.user import UserAlreadyExists, UserNotFound, EmailNotVerified
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.exceptions.media import InvalidImageFile
from luxury_fashion.apps.core.exceptions.contact_exception import ContactNameAlreadyExists, ContactNotFound
from luxury_fashion.apps.core.exceptions.shipping import FrenetAPIError
from luxury_fashion.apps.core.exceptions.cart_exception import CartNotFound
from luxury_fashion.apps.core.exceptions.payment_exception import (
    
    AsaasAPIError,
    OrderNotFound,
    EmptyCart,
    OrderNotPayable,
    OrderAlreadyPaid,
    PaymentNotFound,
    CpfOrCnpjRequired,
    PaymentNotRefundable,
    InvalidWebhookToken,
)

from luxury_fashion.apps.core.exceptions.products_exception import (
    ProductNotFound,
    ProductNameAlreadyExists,
    CategoryNotFound,
    CategoryNameAlreadyExists,
    CategoryHasProducts,
    VariantNotFound,
    VariantAlreadyExists,
    ImageNotFound,
    ShippingNotFound,
    ShippingAlreadyExists,
)

__all__ = [
    
    "InvalidCredentials",
    "InvalidPassword", 
    "InvalidToken",
    "InvalidGoogleToken",
    "SessionNotFound",
    "UserAlreadyExists",
    "UserNotFound",
    "PermissionDenied",
    "EmailNotVerified",
    "InvalidImageFile",
    "ContactNameAlreadyExists",
    "ContactNotFound",

    "FrenetAPIError",

    "CartNotFound",

    "ProductNotFound",
    "ProductNameAlreadyExists",
    "CategoryNotFound",
    "CategoryNameAlreadyExists",
    "CategoryHasProducts",
    "VariantNotFound",
    "VariantAlreadyExists",
    "ImageNotFound",
    "ShippingNotFound",
    "ShippingAlreadyExists",

    "AsaasAPIError",
    "OrderNotFound",
    "EmptyCart",
    "OrderNotPayable",
    "OrderAlreadyPaid",
    "PaymentNotFound",
    "CpfOrCnpjRequired",
    "PaymentNotRefundable",
    "InvalidWebhookToken",
]