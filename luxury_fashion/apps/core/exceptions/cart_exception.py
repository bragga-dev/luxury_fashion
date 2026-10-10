from django.utils.translation import gettext_lazy as _


class InsufficientStock(Exception):
    def __init__(self, message=None):
        self.message = message or _("Estoque insuficiente.")
        super().__init__(self.message)

class CartNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Carrinho não encontrado.")
        super().__init__(self.message)

class CartItemNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Produto não encontrado.")
        super().__init__(self.message)


class ProductUnavailable(Exception):
    def __init__(self, message=None):
        self.message = message or _("Este produto não está disponível no momento.")
        super().__init__(self.message)


class CartPriceChanged(Exception):
    def __init__(self, message=None):
        self.message = message or _("O preço de itens do carrinho mudou. Revise o carrinho antes de finalizar.")
        super().__init__(self.message)


class ShippingOptionUnavailable(Exception):
    def __init__(self, message=None):
        self.message = message or _("Opção de frete indisponível para este carrinho/CEP.")
        super().__init__(self.message)