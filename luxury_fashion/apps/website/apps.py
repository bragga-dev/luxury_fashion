
from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = 'luxury_fashion.apps.website'
    label = 'website'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Web Site'


