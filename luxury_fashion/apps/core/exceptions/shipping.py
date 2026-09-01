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

