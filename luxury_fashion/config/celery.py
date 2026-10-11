from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'luxury_fashion.config.settings.dev')

app = Celery('luxury_fashion')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "expire-pending-orders": {
        "task": "luxury_fashion.apps.payments.tasks.expire_pending_orders.expire_pending_orders",
        "schedule": crontab(minute="*/30"),
    },
}