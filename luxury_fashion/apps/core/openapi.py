"""
Enriquecimento do OpenAPI para geração do cliente TypeScript do front.

O Ninja só declara as respostas que cada rota lista em `response={...}`. Os erros transversais
(401/403 de auth, 422 de validação, 429 de rate limit, 500) são devolvidos pelos handlers globais
de `config/api.py`, mas não aparecem no schema — então o cliente gerado não tem tipo pra eles.
Aqui eles são declarados, apontando pros mesmos schemas que os handlers realmente devolvem.
"""
import copy
import re
from collections import Counter
from typing import Iterable

from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut, ValidationErrorOut

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")

_APP_PREFIX = re.compile(r"^luxury_fashion_apps_[a-z0-9]+_api_")


def _short_operation_id(operation_id: str) -> str:
    short = _APP_PREFIX.sub("", operation_id)
    return short[: -len("_router")] if short.endswith("_router") else short


def _ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _json_response(description: str, schema_name: str) -> dict:
    return {"description": description, "content": {"application/json": {"schema": _ref(schema_name)}}}


def _register_schema(components: dict, model) -> None:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    for name, definition in schema.pop("$defs", {}).items():
        components.setdefault(name, definition)
    components.setdefault(model.__name__, schema)


def operations(schema: dict):
    for path, item in schema.get("paths", {}).items():
        for method in HTTP_METHODS:
            if method in item:
                yield path, method, item[method]


def duplicate_operation_ids(schema: dict) -> list[str]:
    counts = Counter(op.get("operationId") for _, _, op in operations(schema) if op.get("operationId"))
    return sorted(op_id for op_id, n in counts.items() if n > 1)


def enrich_openapi(schema: dict, *, exclude_tags: Iterable[str] = ()) -> dict:
    schema = copy.deepcopy(schema)
    excluded = set(exclude_tags)
    for path in list(schema.get("paths", {})):
        item = schema["paths"][path]
        for method in HTTP_METHODS:
            if method in item and excluded.intersection(item[method].get("tags", [])):
                del item[method]
        if not any(m in item for m in HTTP_METHODS):
            del schema["paths"][path]

    components = schema.setdefault("components", {}).setdefault("schemas", {})
    _register_schema(components, MessageOut)
    _register_schema(components, ValidationErrorOut)
    shortened = {op["operationId"]: _short_operation_id(op["operationId"]) for _, _, op in operations(schema) if op.get("operationId")}
    short_counts = Counter(shortened.values())
    for _, _, op in operations(schema):
        original = op.get("operationId")
        if original and short_counts[shortened[original]] == 1:
            op["operationId"] = shortened[original]

    for _, _, op in operations(schema):
        responses = {str(code): body for code, body in op.setdefault("responses", {}).items()}
        wanted = {}
        if op.get("security"):
            wanted["401"] = _json_response("Não autenticado ou token expirado.", "MessageOut")
            wanted["403"] = _json_response("Sem permissão para este recurso.", "MessageOut")
        if op.get("requestBody") or op.get("parameters"):
            wanted["422"] = _json_response("Dados inválidos (veja `errors`).", "ValidationErrorOut")
        wanted["429"] = _json_response("Muitas requisições. Tente novamente mais tarde.", "MessageOut")
        wanted["500"] = _json_response("Erro interno do servidor.", "MessageOut")
        for code, body in wanted.items():
            responses.setdefault(code, body)
        op["responses"] = responses

    return schema