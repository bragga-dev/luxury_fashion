
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'luxury_fashion.apps.payments'
    label = 'payments'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Pagamentos'


