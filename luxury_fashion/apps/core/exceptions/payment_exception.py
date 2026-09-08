from django.utils.translation import gettext as _


class AsaasAPIError(Exception):

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        payload: dict | None = None,
    ):
        self.message = message or _("Erro ao se comunicar com a Asaas.")
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(self.message)


class OrderNotFound(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Pedido não encontrado.")
        super().__init__(self.message)


class EmptyCart(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Seu carrinho está vazio.")
        super().__init__(self.message)


class OrderNotPayable(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Este pedido não está mais disponível para pagamento."
        )
        super().__init__(self.message)


class OrderAlreadyPaid(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Já existe uma cobrança em aberto ou paga para este pedido."
        )
        super().__init__(self.message)


class PaymentNotFound(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Pagamento não encontrado.")
        super().__init__(self.message)


class CpfOrCnpjRequired(Exception):

    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Informe o CPF ou CNPJ para pagar com cartão de crédito."
        )
        super().__init__(self.message)


class PaymentNotRefundable(Exception):
   
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Essa cobrança não pode ser estornada — só cobranças pagas via "
            "Pix ou cartão, ainda não totalmente estornadas."
        )
        super().__init__(self.message)


class InvalidWebhookToken(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _("Token de webhook inválido.")
        super().__init__(self.message)


class InvalidOrderStatusTransition(Exception):
    def __init__(self, message: str | None = None):
        self.message = message or _(
            "Transição de status inválida para este pedido."
        )
        super().__init__(self.message)