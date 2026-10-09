from django.utils.translation import gettext_lazy as _



class FrenetAPIError(Exception):
    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        payload: dict | None = None,
    ):
        self.message = message or _("Erro ao se comunicar com a Frenet.")
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(self.message)


class FrenetPartnerTokenMissingError(FrenetAPIError):
    """FRENET_PARTNER_TOKEN não configurado."""


class FrenetInsufficientBalanceError(FrenetAPIError):
    """Carteira Frenet sem saldo/limite para comprar a etiqueta (code 3000)."""


class FrenetLabelError(FrenetAPIError):
    """A Frenet recebeu o pedido mas não conseguiu gerar/pagar a etiqueta."""


class OrderLabelNotAllowed(Exception):
    """Pré-condição de negócio não atendida para gerar a etiqueta do pedido."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)