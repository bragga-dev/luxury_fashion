

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'luxury_fashion.apps.cart'
    label = 'cart'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Carrinho'


