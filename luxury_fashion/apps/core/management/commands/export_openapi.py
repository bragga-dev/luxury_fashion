"""
    python manage.py export_openapi [--output openapi.json] [--exclude-tag Webhooks]

Exporta o OpenAPI (com os erros padrão declarados) pra gerar o cliente TypeScript do front.
Funciona mesmo com API_DOCS_ENABLED=False, porque lê o schema direto da API (não da rota /openapi.json).
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

from luxury_fashion.apps.core.openapi import duplicate_operation_ids, enrich_openapi, operations


class Command(BaseCommand):
    help = "Exporta o OpenAPI enriquecido (erros padrão declarados) para gerar o cliente TypeScript do front."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="openapi.json", help="Arquivo de saída (padrão: openapi.json).")
        parser.add_argument(
            "--exclude-tag",
            action="append",
            dest="exclude_tags",
            help="Tag a excluir (repetível). Padrão: Webhooks.",
        )

    def handle(self, *args, **options):
        from luxury_fashion.config.api import api 

        raw = api.get_openapi_schema()
        duplicates = duplicate_operation_ids(raw)
        if duplicates:
            raise CommandError(
                "operationId duplicado (o cliente gerado teria funções com o mesmo nome): " + ", ".join(duplicates)
            )

        exclude = options["exclude_tags"] or ["Webhooks"]
        schema = enrich_openapi(raw, exclude_tags=exclude)

        output = Path(options["output"])
        output.write_text(json.dumps(schema, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), encoding="utf-8")

        total = sum(1 for _ in operations(schema))
        self.stdout.write(self.style.SUCCESS(f"OpenAPI exportado em {output} ({total} operações; tags excluídas: {', '.join(exclude)})."))