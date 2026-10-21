"""Sentry: desligado sem DSN e, quando ligado, sem PII, sem corpo de requisição e com campos sensíveis filtrados."""
import pytest
import sentry_sdk

from luxury_fashion.config.sentry import build_event_scrubber, init_sentry

NO_PATCHING = {"integrations": [], "default_integrations": False, "auto_enabling_integrations": False}


@pytest.fixture(autouse=True)
def _reset_sentry():
    yield
    sentry_sdk.init(dsn="", **NO_PATCHING)


class TestInit:
    def test_does_nothing_without_dsn(self, monkeypatch):
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert init_sentry(**NO_PATCHING) is False
        assert not sentry_sdk.get_client().is_active()

    def test_blank_dsn_counts_as_disabled(self, monkeypatch):
        monkeypatch.setenv("SENTRY_DSN", "   ")
        assert init_sentry(**NO_PATCHING) is False

    def test_enabled_with_privacy_safe_options(self, monkeypatch):
        monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/1")
        monkeypatch.setenv("SENTRY_ENVIRONMENT", "staging")
        monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")
        assert init_sentry(**NO_PATCHING) is True
        client = sentry_sdk.get_client()
        options = client.options
        assert client.should_send_default_pii() is False
        assert options["event_scrubber"] is not None  
        assert options["max_request_body_size"] == "never"
        assert options["environment"] == "staging"
        assert options["traces_sample_rate"] == pytest.approx(0.2)


def is_filtered(value) -> bool:
    """O scrubber troca o valor por um AnnotatedValue (vira "[Filtered]" ao serializar o evento)."""
    return type(value).__name__ == "AnnotatedValue"


class TestScrubber:
    def test_filters_sensitive_keys_recursively(self):
        event = {
            "extra": {
                "cpf": "123.456.789-09",
                "password": "SenhaSecreta123",
                "refresh_token": "abc.def.ghi",
                "payment_pix_copy_paste": "000201...",
                "order_code": "ORD-1",
                "cliente": {"email": "a@b.com", "telefone": "+5573999999999", "cidade": "Jequié"},
            },
            "request": {"headers": {"Authorization": "Bearer xyz", "Accept": "application/json"}},
        }
        build_event_scrubber().scrub_event(event)
        extra = event["extra"]
        for key in ("cpf", "password", "refresh_token", "payment_pix_copy_paste"):
            assert is_filtered(extra[key]), key
        assert is_filtered(extra["cliente"]["email"]) and is_filtered(extra["cliente"]["telefone"])
        assert is_filtered(event["request"]["headers"]["Authorization"])
        assert extra["order_code"] == "ORD-1"
        assert extra["cliente"]["cidade"] == "Jequié"
        assert event["request"]["headers"]["Accept"] == "application/json"