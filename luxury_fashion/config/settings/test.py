"""
Settings de teste — banco sqlite em memória (não depende de Postgres
rodando), Celery síncrono (sem broker), rate limit desligado e envio de
e-mail em memória. Nada aqui chama serviço externo de verdade; a Asaas é
sempre mockada nos testes.
"""
from .base import *  # noqa

DEBUG = False

SECRET_KEY = env("SECRET_KEY", default="test-secret-key")

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_CACHE_BACKEND = "memory"

# django-ratelimit: desliga nos testes pra não derrubar chamadas repetidas
# de teste que batem no mesmo endpoint várias vezes.
RATELIMIT_ENABLE = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]