# type: ignore
"""
Sentry — monitoramento de erros do back (Django + Celery).

Só liga se `SENTRY_DSN` estiver definido; sem ele, `init_sentry()` não faz nada (dev/CI ficam intactos).

LGPD — o que NUNCA sai daqui:
  - sem PII: IP, cookies e dados do usuário logado não são enviados. Não passamos `send_default_pii`
    porque o SDK 2.72 o deprecou em favor de `data_collection`, e o padrão do SDK já é "sem PII"
    (`should_send_default_pii() is False`);
  - `max_request_body_size="never"`: o corpo das requisições (senha, CPF, endereço) não é enviado;
  - EventScrubber com denylist ampliada (CPF, telefone, tokens, PIX, e-mail...) varrendo
    `extra`, contexto, breadcrumbs e as variáveis locais dos frames do stack trace.

Por que NÃO usar `data_collection` aqui: com ele configurado o SDK desativa o EventScrubber, e é o
scrubber que carrega os termos brasileiros (CPF, telefone, PIX). Se um dia migrar pra `data_collection`,
reporte os mesmos termos em `extra_terms`.
"""
import logging
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, DEFAULT_PII_DENYLIST, EventScrubber

EXTRA_DENYLIST = [
    "cpf", "cnpj", "rg", "phone", "telefone", "celular", "email", "birth_date", "data_nascimento",
    "cep", "street", "address", "access", "refresh", "refresh_token", "access_token",
    "senha", "pix", "payment_pix_copy_paste", "payment_pix_qr_code", "card_number", "cvv",
]


def build_event_scrubber() -> EventScrubber:
    return EventScrubber(
        denylist=DEFAULT_DENYLIST + EXTRA_DENYLIST,
        pii_denylist=DEFAULT_PII_DENYLIST,
        recursive=True,
    )


def init_sentry(**overrides) -> bool:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    options = {
        "dsn": dsn,
        "environment": os.environ.get("SENTRY_ENVIRONMENT", "production"),
        "release": os.environ.get("SENTRY_RELEASE") or None,
        "traces_sample_rate": float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0") or 0),
        "max_request_body_size": "never",
        "event_scrubber": build_event_scrubber(),
        "integrations": [
            DjangoIntegration(),
            CeleryIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    }
    options.update(overrides)
    sentry_sdk.init(**options)
    return True