# luxury_fashion/luxury_fashion/config/__init__.py
# Carrega o app Celery junto com o Django (padrão oficial). Sem isso, `task.delay()` chamado pela API
# usa um app Celery "padrão" que ignora as settings CELERY_* (serializer, timezone, eager nos testes...)
# e só funciona porque a variável de ambiente CELERY_BROKER_URL coincide com a do worker.
from .celery import app as celery_app

__all__ = ("celery_app",)