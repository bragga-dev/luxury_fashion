import logging
import requests
from django.conf import settings
from luxury_fashion.apps.core.exceptions.shipping import FrenetAPIError


logger = logging.getLogger(__name__)


class FrenetClient:
    """
    Wrapper fino sobre a API REST da Frenet.

    Responsabilidades:
    - montar requisições para a Frenet;
    - enviar autenticação;
    - tratar erros HTTP e de conexão;
    - registrar requests/responses de forma segura.

    Nenhuma regra de negócio deve ficar aqui.
    Regras relacionadas ao cálculo de frete da loja ficam no
    product_shipping_service.

    Configurações:
    - FRENET_BASE_URL
    - FRENET_API_KEY
    """

    def __init__(self):
        self.base_url = settings.FRENET_BASE_URL.rstrip("/")
        self.session = requests.Session()

        self.session.headers.update(
            {
                "token": settings.FRENET_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": "luxury-fashion",
            }
        )

    def _request(self, method: str, path: str, **kwargs,) -> dict:
        """
        Executa uma requisição HTTP contra a API da Frenet.

        Centraliza:
        - URL;
        - timeout;
        - tratamento de conexão;
        - logging;
        - tratamento de erros HTTP;
        - parsing da resposta JSON.
        """

        url = f"{self.base_url}{path}"
        logger.info("Frenet request: %s %s | body=%s", method, url, kwargs.get("json"),)

        try:
            response = self.session.request(method, url, timeout=15, **kwargs)

        except requests.RequestException as exc:
            logger.exception("Falha de conexão com a Frenet: %s %s", method, url)

            raise FrenetAPIError(f"Falha de conexão com a Frenet: {exc}") from exc

        logger.info("Frenet response: %s %s -> %s | body=%r", method, url, response.status_code, response.text[:500])

        if not response.ok:
            payload = {}
            message = response.text

            try:
                payload = response.json()
                message = (
                    payload.get("Message")
                    or payload.get("message")
                    or payload.get("Error")
                    or payload.get("error")
                    or response.text
                )

            except (ValueError, AttributeError):
                pass

            if not message:
                message = (f"Frenet retornou HTTP {response.status_code} " f"para {method} {path}.")

            raise FrenetAPIError(message, status_code=response.status_code, payload=payload,)

        if response.status_code == 204 or not response.content:
            return {}

        try:
            return response.json()

        except ValueError as exc:
            raise FrenetAPIError("A Frenet retornou uma resposta inválida.") from exc

    # ─────────────────────────────────────────────────────────────
    # Shipping
    # ─────────────────────────────────────────────────────────────

    def calculate_shipping(
        self,
        *,
        seller_cep: str,
        recipient_cep: str,
        weight: float,
        height: float,
        width: float,
        length: float,
        invoice_value: float,
        quantity: int = 1,
    ) -> dict:
        """
        Consulta as opções de frete disponíveis para uma remessa.

        Não contém regra de negócio da aplicação.
        Apenas transforma os argumentos no payload esperado pela Frenet.
        """

        payload = {
            "SellerCEP": str(seller_cep),
            "RecipientCEP": str(recipient_cep),
            "ShipmentInvoiceValue": round(float(invoice_value), 2),
            "ShippingItemArray": [
                {
                    "Weight": float(weight),
                    "Length": float(length),
                    "Height": float(height),
                    "Width": float(width),
                    "Quantity": int(quantity),
                }
            ],
        }

        return self._request("POST", "/shipping/quote", json=payload)