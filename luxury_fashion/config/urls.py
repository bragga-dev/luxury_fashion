from luxury_fashion.apps.core import health
from luxury_fashion.config.api import api
from django.conf import settings
from django.contrib import admin
from django.urls import path


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("health/live", health.live, name="health-live"),
    path("health/ready", health.ready, name="health-ready"),
    path("api/", api.urls),
]