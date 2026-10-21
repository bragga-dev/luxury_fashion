export DJANGO_SETTINGS_MODULE=luxury_fashion.config.settings.test
pytest luxury_fashion/apps/payments/tests --cov=luxury_fashion/apps/payments --cov-report=term-missing


pytest -c pytes.ini luxury_fashion/apps --cov=luxury_fashion/apps --cov-report=term-missing


pytest -c pytes.ini luxury_fashion/apps --cov

pytest luxury_fashion/apps --cov