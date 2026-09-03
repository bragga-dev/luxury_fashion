from django.utils.translation import gettext_lazy as _


class CartNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Carrinho não encontrado.")
        super().__init__(self.message)

class CartItemNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Produto não encontrado.")
        super().__init__(self.message)


class InsufficientStock(Exception):
    def __init__(self, message=None):
        self.message = message or _("Estoque insuficiente.")
        super().__init__(self.message)

