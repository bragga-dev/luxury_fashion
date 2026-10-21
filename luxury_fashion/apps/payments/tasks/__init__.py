# luxury_fashion/luxury_fashion/apps/payments/tasks/__init__.py
# Importa os módulos pra o Celery registrar as tasks (autodiscover só carrega o pacote `tasks`).
# Import de módulo (e não de função) pra não sobrescrever o atributo do pacote e manter válidos os
# caminhos de mock.patch("...tasks.<modulo>.<nome>") dos testes.
from . import expire_pending_orders, order_notifications, send_payment_request  # noqa: F401