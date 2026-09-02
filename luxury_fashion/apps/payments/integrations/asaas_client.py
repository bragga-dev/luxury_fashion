import logging

import requests
from django.conf import settings
from luxury_fashion.apps.core.exceptions.payment_exception import AsaasAPIError

logger = logging.getLogger(__name__)


class AsaasClient:
    def __init__(self):
        self.base_url = settings.ASAAS_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "access_token": settings.ASAAS_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "beauty-formula",
        })

    @staticmethod
    def _redact_body(body):
        if not isinstance(body, dict) or "cpfCnpj" not in body:
            return body
        redacted = dict(body)
        redacted["cpfCnpj"] = "***"
        return redacted

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        masked_key = settings.ASAAS_API_KEY
        if masked_key and len(masked_key) > 14:
            masked_key = f"{masked_key[:8]}...{masked_key[-6:]}"
        logger.info("Asaas request: %s %s | access_token=%s | body=%s", method, url, masked_key, self._redact_body(kwargs.get("json")),)

        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as e:
            raise AsaasAPIError(f"Falha de conexão com a Asaas: {e}")

        logger.info("Asaas response: %s %s -> %s | headers=%s | body=%r", method, url, response.status_code, dict(response.headers), response.text[:500],)

        if not response.ok:
            payload = {}
            message = response.text
            try:
                payload = response.json()
                message = payload.get("errors", [{}])[0].get("description", response.text)
            except (ValueError, IndexError, KeyError):
                pass

            if not message:
                message = (
                    f"Asaas retornou {response.status_code} sem corpo de resposta "
                    f"para {method} {path}. Veja o log 'Asaas request/response' "
                    "logo acima pra conferir URL, corpo e headers de resposta."
                )

            raise AsaasAPIError(message, status_code=response.status_code, payload=payload)

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ── Payments (Cobranças) ─────────────────────────────────────────────

    def create_payment(
        self,
        *,
        customer_id: str,
        billing_type: str,
        value: float,
        due_date: str,
        description: str = None,
        external_reference: str = None,
    ) -> dict:
        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": round(float(value), 2),
            "dueDate": due_date,
            "description": description,
            "externalReference": external_reference,
        }
       
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/payments", json=payload)

    def get_payment(self, payment_id: str) -> dict:
        return self._request("GET", f"/payments/{payment_id}")

    def get_pix_qrcode(self, payment_id: str) -> dict:
        """Só retorna algo útil se billingType da cobrança for PIX (ou UNDEFINED)."""
        return self._request("GET", f"/payments/{payment_id}/pixQrCode")

    def cancel_payment(self, payment_id: str) -> dict:
        return self._request("DELETE", f"/payments/{payment_id}")

    # ── Customers (Clientes) ─────────────────────────────────────────────

    def create_customer(
        self,
        *,
        name: str,
        cpf_cnpj: str,
        email: str = None,
        external_reference: str = None,
    ) -> dict:
        payload = {
            "name": name,
            "cpfCnpj": cpf_cnpj,
            "email": email,
            "externalReference": external_reference,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/customers", json=payload)

    def refund_payment(self, payment_id: str, *, value: float = None, description: str = None) -> dict:
        payload = {"value": value, "description": description}
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", f"/payments/{payment_id}/refund", json=payload)