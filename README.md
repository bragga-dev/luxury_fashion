export DJANGO_SETTINGS_MODULE=luxury_fashion.config.settings.test
pytest luxury_fashion/apps/payments/tests --cov=luxury_fashion/apps/payments --cov-report=term-missing