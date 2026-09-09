"""
Testes do AsaasClient — a camada mais baixa (HTTP puro) da integração.
`session.request` é sempre mockado; nenhum destes testes toca a rede.
"""
import json
from unittest.mock import MagicMock

import pytest
import requests

from luxury_fashion.apps.core.exceptions import AsaasAPIError
from luxury_fashion.apps.payments.integrations.asaas_client import AsaasClient

pytestmark = pytest.mark.django_db


def _response(status_code=200, json_body=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 400
    resp.headers = {}
    resp.content = b"1" if (json_body is not None or text) else b""
    resp.text = text if text else (json.dumps(json_body) if json_body is not None else "")
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


class TestAsaasClientRequests:
    def test_create_payment_sends_expected_payload(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(200, {"id": "pay_1", "status": "PENDING"}))
        monkeypatch.setattr(client.session, "request", fake_request)

        result = client.create_payment(
            customer_id="cus_1", billing_type="PIX", value=10.5, due_date="2026-01-01"
        )

        assert result == {"id": "pay_1", "status": "PENDING"}
        sent_json = fake_request.call_args.kwargs["json"]
        assert sent_json["customer"] == "cus_1"
        assert sent_json["value"] == 10.5
        assert "description" not in sent_json  # None values não são enviados

    def test_get_pix_qrcode_hits_correct_path(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(200, {"encodedImage": "x"}))
        monkeypatch.setattr(client.session, "request", fake_request)

        client.get_pix_qrcode("pay_1")

        args, kwargs = fake_request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/payments/pay_1/pixQrCode")

    def test_raises_asaas_api_error_on_http_error_with_body(self, monkeypatch):
        client = AsaasClient()
        error_body = {"errors": [{"description": "Cliente inválido"}]}
        fake_request = MagicMock(return_value=_response(400, error_body, text=json.dumps(error_body)))
        monkeypatch.setattr(client.session, "request", fake_request)

        with pytest.raises(AsaasAPIError) as exc_info:
            client.create_payment(customer_id="cus_x", billing_type="PIX", value=10, due_date="2026-01-01")
        assert "Cliente inválido" in str(exc_info.value)

    def test_raises_asaas_api_error_on_http_error_without_body(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(500, None, text=""))
        monkeypatch.setattr(client.session, "request", fake_request)

        with pytest.raises(AsaasAPIError):
            client.get_payment("pay_1")

    def test_raises_asaas_api_error_on_connection_failure(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(side_effect=requests.ConnectionError("boom"))
        monkeypatch.setattr(client.session, "request", fake_request)

        with pytest.raises(AsaasAPIError):
            client.get_payment("pay_1")

    def test_no_content_response_returns_empty_dict(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(204))
        monkeypatch.setattr(client.session, "request", fake_request)

        assert client.cancel_payment("pay_1") == {}

    def test_refund_payment_only_sends_provided_fields(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(200, {"status": "REFUNDED"}))
        monkeypatch.setattr(client.session, "request", fake_request)

        client.refund_payment("pay_1")

        sent_json = fake_request.call_args.kwargs["json"]
        assert sent_json == {}

    def test_create_customer_builds_expected_payload(self, monkeypatch):
        client = AsaasClient()
        fake_request = MagicMock(return_value=_response(200, {"id": "cus_1"}))
        monkeypatch.setattr(client.session, "request", fake_request)

        client.create_customer(name="Maria", cpf_cnpj="39053344705", email="maria@example.com")

        sent_json = fake_request.call_args.kwargs["json"]
        assert sent_json == {
            "name": "Maria",
            "cpfCnpj": "39053344705",
            "email": "maria@example.com",
        }


class TestRedactBody:
    def test_redacts_cpf_cnpj(self):
        redacted = AsaasClient._redact_body({"cpfCnpj": "39053344705"})
        assert redacted["cpfCnpj"] == "***"

    def test_redacts_credit_card_fields(self):
        redacted = AsaasClient._redact_body(
            {"creditCard": {"holderName": "Maria", "number": "4111111111111111"}}
        )
        assert redacted["creditCard"]["number"] == "***"
        assert redacted["creditCard"]["holderName"] == "***"

    def test_redacts_credit_card_holder_info(self):
        redacted = AsaasClient._redact_body(
            {"creditCardHolderInfo": {"cpfCnpj": "39053344705", "email": "a@a.com"}}
        )
        assert redacted["creditCardHolderInfo"]["cpfCnpj"] == "***"
        assert redacted["creditCardHolderInfo"]["email"] == "***"

    def test_non_dict_body_is_returned_unchanged(self):
        assert AsaasClient._redact_body(None) is None
        assert AsaasClient._redact_body("texto") == "texto"
