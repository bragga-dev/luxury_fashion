from django.utils.translation import gettext_lazy as _


class PermissionDenied(Exception):
    """Exceção lançada quando um usuário não tem permissão."""
    def __init__(self, msg: str = "Você não tem permissão para realizar esta ação."):
        super().__init__(_(msg))

class ClientNotFoundError(Exception):
    """Exceção lançada quando o cliente não é encontrado."""
    pass


class ClientNotActiveError(Exception):
    """Exceção lançada quando o client não está ativo na funcionário."""
    pass