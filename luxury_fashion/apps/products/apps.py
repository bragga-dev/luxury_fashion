from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = 'luxury_fashion.apps.products'
    label = 'products'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Produtos'