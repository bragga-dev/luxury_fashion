# luxury_fashion/luxury_fashion/apps/notifications/tasks/__init__.py
# Importa os módulos pra o Celery registrar as tasks (autodiscover só carrega o pacote `tasks`).
from . import cleanup_notifications, send_review_requests  # noqa: F401