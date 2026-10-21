"""OpenAPI exportado: operationIds únicos, erros padrão declarados, refs válidas, webhooks fora."""
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from luxury_fashion.apps.core.openapi import duplicate_operation_ids, enrich_openapi, operations


def _schema(**op):
    return {"paths": {"/x": {"post": {"operationId": "x_post", "tags": ["T"], "responses": {200: {"description": "ok"}}, **op}}}}


class TestEnrichOpenapi:
    def test_adds_auth_errors_only_to_secured_operations(self):
        secured = enrich_openapi(_schema(security=[{"JWTAuth": []}]))["paths"]["/x"]["post"]["responses"]
        public = enrich_openapi(_schema())["paths"]["/x"]["post"]["responses"]
        assert {"401", "403"} <= set(secured)
        assert not {"401", "403"} & set(public)

    def test_adds_422_only_when_there_is_input(self):
        with_body = enrich_openapi(_schema(requestBody={"content": {}}))["paths"]["/x"]["post"]["responses"]
        without = enrich_openapi(_schema())["paths"]["/x"]["post"]["responses"]
        assert "422" in with_body and "422" not in without

    def test_always_adds_429_and_500(self):
        responses = enrich_openapi(_schema())["paths"]["/x"]["post"]["responses"]
        assert {"429", "500"} <= set(responses)

    def test_never_overrides_declared_responses_and_normalizes_keys_to_str(self):
        custom = {"description": "meu 404"}
        schema = _schema(security=[{"JWTAuth": []}])
        schema["paths"]["/x"]["post"]["responses"][401] = custom
        responses = enrich_openapi(schema)["paths"]["/x"]["post"]["responses"]
        assert responses["401"] == custom
        assert all(isinstance(code, str) for code in responses)

    def test_is_idempotent(self):
        once = enrich_openapi(_schema(security=[{"JWTAuth": []}], requestBody={"content": {}}))
        assert enrich_openapi(once) == once

    def test_registers_error_schemas_with_nested_definition(self):
        schemas = enrich_openapi(_schema())["components"]["schemas"]
        assert {"MessageOut", "ValidationErrorOut", "FieldErrorOut"} <= set(schemas)

    def test_excludes_tags_and_drops_empty_paths(self):
        schema = _schema()
        schema["paths"]["/hook"] = {"post": {"operationId": "hook", "tags": ["Webhooks"], "responses": {}}}
        result = enrich_openapi(schema, exclude_tags=["Webhooks"])
        assert "/hook" not in result["paths"] and "/x" in result["paths"]

    def test_does_not_mutate_the_input(self):
        schema = _schema()
        enrich_openapi(schema)
        assert set(schema["paths"]["/x"]["post"]["responses"]) == {200}

    def test_shortens_operation_ids(self):
        schema = {"paths": {"/a": {"post": {"operationId": "luxury_fashion_apps_accounts_api_auth_login_router", "responses": {}}}}}
        op = enrich_openapi(schema)["paths"]["/a"]["post"]
        assert op["operationId"] == "auth_login"

    def test_keeps_the_long_name_when_the_short_one_would_collide(self):
        a = "luxury_fashion_apps_accounts_api_auth_ping_router"
        b = "luxury_fashion_apps_payments_api_auth_ping_router"
        schema = {"paths": {"/a": {"get": {"operationId": a, "responses": {}}}, "/b": {"get": {"operationId": b, "responses": {}}}}}
        enriched = enrich_openapi(schema)["paths"]
        assert enriched["/a"]["get"]["operationId"] == a and enriched["/b"]["get"]["operationId"] == b

    def test_shortening_is_idempotent(self):
        schema = {"paths": {"/a": {"post": {"operationId": "luxury_fashion_apps_accounts_api_auth_login_router", "responses": {}}}}}
        once = enrich_openapi(schema)
        assert enrich_openapi(once) == once

    def test_duplicate_operation_ids_are_detected(self):
        schema = _schema()
        schema["paths"]["/y"] = {"get": {"operationId": "x_post", "responses": {}}}
        assert duplicate_operation_ids(schema) == ["x_post"]


@pytest.fixture(scope="module")
def raw():
    from luxury_fashion.config.api import api
    return api.get_openapi_schema()


class TestRealApiSchema:
    def test_operation_ids_are_unique(self, raw):
        assert duplicate_operation_ids(raw) == []

    def test_every_ref_resolves(self, raw):
        enriched = enrich_openapi(raw, exclude_tags=["Webhooks"])
        names = set(enriched["components"]["schemas"])
        refs = set()

        def walk(node):
            if isinstance(node, dict):
                if "$ref" in node:
                    refs.add(node["$ref"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(enriched)
        missing = {r for r in refs if r.startswith("#/components/schemas/") and r.rsplit("/", 1)[1] not in names}
        assert not missing

    def test_every_operation_declares_500_and_422_when_it_takes_input(self, raw):
        enriched = enrich_openapi(raw, exclude_tags=["Webhooks"])
        for path, method, op in operations(enriched):
            assert "500" in op["responses"], f"{method.upper()} {path}"
            if op.get("requestBody") or op.get("parameters"):
                assert "422" in op["responses"], f"{method.upper()} {path}"

    def test_enriched_operation_ids_are_short_and_unique(self, raw):
        enriched = enrich_openapi(raw, exclude_tags=["Webhooks"])
        ids = [op["operationId"] for _, _, op in operations(enriched)]
        assert len(ids) == len(set(ids))
        assert not [i for i in ids if i.startswith("luxury_fashion_apps_")]

    def test_notification_and_order_admin_routes_are_in_the_contract(self, raw):
        paths = enrich_openapi(raw)["paths"]
        for expected in ("/api/notifications/", "/api/notifications/unread-count", "/api/orders/admin/list",
                         "/api/orders/admin/summary", "/api/orders/{order_id}/mark-delivered"):
            assert expected in paths, expected


class TestExportCommand:
    def test_writes_enriched_schema_without_webhooks(self, tmp_path):
        out = tmp_path / "openapi.json"
        call_command("export_openapi", output=str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["paths"]
        tags = {tag for _, _, op in operations(data) for tag in op.get("tags", [])}
        assert "Webhooks" not in tags
        assert "ValidationErrorOut" in data["components"]["schemas"]

    def test_fails_on_duplicate_operation_ids(self, tmp_path):
        from unittest.mock import patch
        dup = {"paths": {"/a": {"get": {"operationId": "same", "responses": {}}}, "/b": {"get": {"operationId": "same", "responses": {}}}}}
        with patch("luxury_fashion.config.api.api.get_openapi_schema", return_value=dup):
            with pytest.raises(CommandError, match="same"):
                call_command("export_openapi", output=str(tmp_path / "o.json"))