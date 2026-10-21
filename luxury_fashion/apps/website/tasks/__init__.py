# luxury_fashion/luxury_fashion/apps/website/tasks/__init__.py
# Importa o módulo pra o Celery registrar as tasks (o autodiscover só carrega o pacote `tasks`).
from . import contact_notifications  # noqa: F401