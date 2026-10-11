import logging
import requests
from django.conf import settings
from luxury_fashion.apps.core.exceptions.shipping import (
    FrenetAPIError,
    FrenetInsufficientBalanceError,
    FrenetPartnerTokenMissingError,
)


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
    - FRENET_BASE_URL (cotação) / FRENET_API_KEY (token do cliente)
    - FRENET_WHITELABEL_BASE_URL / FRENET_PARTNER_TOKEN (etiquetas OneClick)
    """

    INSUFFICIENT_BALANCE_CODE = 3000

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

    def _request(
        self,
        method: str,
        path: str,
        *,
        base_url: str | None = None,
        timeout: int = 15,
        log_body: bool = True,
        **kwargs,
    ) -> dict:
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

        url = f"{(base_url or self.base_url).rstrip('/')}{path}"
        # log_body=False em payloads com PII (CPF, telefone, endereço).
        logger.info("Frenet request: %s %s | body=%s", method, url, kwargs.get("json") if log_body else "<omitido>")

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)

        except requests.RequestException as exc:
            logger.exception("Falha de conexão com a Frenet: %s %s", method, url)

            raise FrenetAPIError(f"Falha de conexão com a Frenet: {exc}") from exc

        logger.info("Frenet response: %s %s -> %s | body=%r", method, url, response.status_code, response.text[:1000])

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

            details = payload.get("Details") if isinstance(payload, dict) else None
            if details:
                joined = "; ".join(f"[{d.get('Code')}] {d.get('Message')}" for d in details if isinstance(d, dict))
                message = f"{message} — {joined}" if message else joined

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

    def calculate_shipping_for_items(
        self,
        *,
        seller_cep: str,
        recipient_cep: str,
        items: list[dict],
        invoice_value: float,
    ) -> dict:
        """
        Cotação de uma remessa com VÁRIOS itens (carrinho inteiro) numa chamada só.

        Cada item: {"weight", "length", "height", "width", "quantity"} (peso/dimensões
        por unidade). Sem regra de negócio — só monta o payload da Frenet.
        """
        payload = {
            "SellerCEP": str(seller_cep),
            "RecipientCEP": str(recipient_cep),
            "ShipmentInvoiceValue": round(float(invoice_value), 2),
            "ShippingItemArray": [
                {
                    "Weight": float(i["weight"]),
                    "Length": float(i["length"]),
                    "Height": float(i["height"]),
                    "Width": float(i["width"]),
                    "Quantity": int(i["quantity"]),
                }
                for i in items
            ],
        }
        return self._request("POST", "/shipping/quote", json=payload)

    # ─────────────────────────────────────────────────────────────
    # Orders OneClick (API Whitelabel)
    # ─────────────────────────────────────────────────────────────

    def create_order_oneclick(self, shipments: list[dict]) -> dict:
        """
        Cria o pedido na Frenet, paga com o saldo da carteira e gera a etiqueta
        numa única chamada (POST /v1/orders/oneclick).

        Auth: `token` (cliente, já no session) + `x-partner-token`.
        Retorna o ShipmentBatchResult cru; interpretação fica no service.

        ATENÇÃO: a chamada gasta saldo. Timeout aqui NÃO significa que nada
        aconteceu — o service não deve reenviar sem checar o painel/Order.Id.
        """
        if not settings.FRENET_PARTNER_TOKEN:
            raise FrenetPartnerTokenMissingError(
                "Geração de etiqueta indisponível: FRENET_PARTNER_TOKEN não configurado."
            )

        headers = {"x-partner-token": settings.FRENET_PARTNER_TOKEN}
        if settings.FRENET_PRINTING_FORMAT:
            headers["x-printing-format"] = settings.FRENET_PRINTING_FORMAT

        try:
            return self._request(
                "POST",
                "/v1/orders/oneclick",
                base_url=settings.FRENET_WHITELABEL_BASE_URL,
                headers=headers,
                json=shipments,
                timeout=60,
                log_body=False,
            )
        except FrenetAPIError as exc:
            if self._has_error_code(exc.payload, self.INSUFFICIENT_BALANCE_CODE):
                raise FrenetInsufficientBalanceError(
                    "Saldo insuficiente na carteira Frenet para gerar a etiqueta.",
                    status_code=exc.status_code,
                    payload=exc.payload,
                ) from exc
            raise

    @staticmethod
    def _has_error_code(payload: dict, code: int) -> bool:
        details = (payload or {}).get("Details") or []
        return any(isinstance(d, dict) and d.get("Code") == code for d in details)