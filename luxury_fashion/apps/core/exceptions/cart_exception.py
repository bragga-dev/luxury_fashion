from django.utils.translation import gettext_lazy as _


class InsufficientStock(Exception):
    def __init__(self, message=None):
        self.message = message or _("Estoque insuficiente.")
        super().__init__(self.message)