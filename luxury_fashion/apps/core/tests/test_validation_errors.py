"""Contrato do 422: `detail` sempre texto + `errors` por campo, sem eco dos valores enviados."""
import pytest

from luxury_fashion.apps.core.utils.validation_errors import format_validation_errors

pytestmark = pytest.mark.django_db


class TestValidationErrorResponse:
    def test_body_errors_use_field_names_without_ninja_prefix(self, client):
        resp = client.post("/api/auth/login", data={}, content_type="application/json")
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"] == "Dados inválidos."
        assert {e["field"] for e in body["errors"]} == {"email", "password"}
        assert all(set(e) == {"field", "message", "type"} for e in body["errors"])
        assert {e["type"] for e in body["errors"]} == {"missing"}

    def test_query_errors_use_the_parameter_name(self, client):
        resp = client.get("/api/products/?page=abc")
        assert resp.status_code == 422
        assert resp.json()["errors"][0]["field"] == "page"
        assert resp.json()["errors"][0]["type"] == "int_parsing"

    def test_detail_is_text_like_every_other_error(self, client):
        resp = client.post("/api/auth/login", data={}, content_type="application/json")
        assert isinstance(resp.json()["detail"], str)


class TestFormatValidationErrors:
    def test_never_echoes_input_or_ctx(self):
        errors = [{
            "type": "string_too_short",
            "loc": ["body", "payload", "password"],
            "msg": "String should have at least 8 characters",
            "input": "SenhaSecreta123",
            "ctx": {"min_length": 8},
        }]
        result = format_validation_errors(errors)
        assert result == [{"field": "password", "message": "String should have at least 8 characters", "type": "string_too_short"}]
        assert "SenhaSecreta123" not in str(result)

    def test_nested_and_indexed_paths(self):
        errors = [{"type": "missing", "loc": ["body", "payload", "items", 0, "quantity"], "msg": "Field required"}]
        assert format_validation_errors(errors)[0]["field"] == "items.0.quantity"

    def test_whole_body_error_has_empty_field(self):
        errors = [{"type": "model_attributes_type", "loc": ["body", "payload"], "msg": "Input should be a valid dictionary"}]
        assert format_validation_errors(errors)[0]["field"] == ""

    def test_path_and_header_sources_are_stripped_too(self):
        errors = [{"type": "uuid_parsing", "loc": ["path", "order_id"], "msg": "Input should be a valid UUID"}]
        assert format_validation_errors(errors)[0]["field"] == "order_id"