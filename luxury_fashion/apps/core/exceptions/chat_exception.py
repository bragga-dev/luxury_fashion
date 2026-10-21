from django.utils.translation import gettext_lazy as _


class ConversationNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Conversa não encontrada.")
        super().__init__(self.message)


class MessageNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Mensagem não encontrada.")
        super().__init__(self.message)


class EmptyMessage(Exception):
    def __init__(self, message=None):
        self.message = message or _("A mensagem precisa ter texto ou pelo menos um anexo.")
        super().__init__(self.message)


class TooManyAttachments(Exception):
    def __init__(self, message=None):
        self.message = message or _("Número máximo de anexos por mensagem excedido.")
        super().__init__(self.message)