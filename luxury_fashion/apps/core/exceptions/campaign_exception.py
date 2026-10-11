from django.utils.translation import gettext_lazy as _


class CampaignNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Campanha não encontrada.")
        super().__init__(self.message)


class CampaignTitleAlreadyExists(Exception):
    def __init__(self, message=None):
        self.message = message or _("Já existe uma campanha com esse título.")
        super().__init__(self.message)


class CampaignImageNotFound(Exception):
    def __init__(self, message=None):
        self.message = message or _("Imagem da campanha não encontrada.")
        super().__init__(self.message)