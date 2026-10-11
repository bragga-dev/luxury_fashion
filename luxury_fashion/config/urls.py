from luxury_fashion.config.api import api
from django.conf import settings
from django.contrib import admin
from django.urls import path


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/", api.urls),
]