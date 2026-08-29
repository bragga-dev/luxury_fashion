from django.utils.translation import gettext_lazy as _

# ── Exceções de Existência ──────────────────────────────────────────────────

class AddressNotFound(Exception):
    """Lançada quando um endereço não é encontrado."""
    def __init__(self, message=None):
        self.message = message or _("Endereço não encontrado.")
        super().__init__(self.message)


class AddressesNotFound(Exception):
    """Lançada quando nenhum endereço é encontrado para um cliente."""
    def __init__(self, message=None):
        self.message = message or _("Nenhum endereço encontrado para este cliente.")
        super().__init__(self.message)


class PreferentialAddressNotFound(Exception):
    """Lançada quando um endereço preferencial não é encontrado."""
    def __init__(self, message=None):
        self.message = message or _("Endereço preferencial não encontrado.")
        super().__init__(self.message)


# ── Exceções de Criação/Atualização ────────────────────────────────────────

class AddressCreationError(Exception):
    """Lançada quando ocorre um erro ao criar um endereço."""
    def __init__(self, message=None):
        self.message = message or _("Erro ao criar endereço.")
        super().__init__(self.message)


class AddressUpdateError(Exception):
    """Lançada quando ocorre um erro ao atualizar um endereço."""
    def __init__(self, message=None):
        self.message = message or _("Erro ao atualizar endereço.")
        super().__init__(self.message)


class AddressDeletionError(Exception):
    """Lançada quando ocorre um erro ao deletar um endereço."""
    def __init__(self, message=None):
        self.message = message or _("Erro ao deletar endereço.")
        super().__init__(self.message)


# ── Exceções de Validação ──────────────────────────────────────────────────

class InvalidAddressData(Exception):
    """Lançada quando os dados do endereço são inválidos."""
    def __init__(self, message=None):
        self.message = message or _("Dados do endereço inválidos.")
        super().__init__(self.message)


class InvalidCEP(Exception):
    """Lançada quando o CEP é inválido."""
    def __init__(self, message=None):
        self.message = message or _("CEP inválido.")
        super().__init__(self.message)


class InvalidState(Exception):
    """Lançada quando o estado é inválido."""
    def __init__(self, message=None):
        self.message = message or _("Estado inválido.")
        super().__init__(self.message)


class InvalidCity(Exception):
    """Lançada quando a cidade é inválida."""
    def __init__(self, message=None):
        self.message = message or _("Cidade inválida.")
        super().__init__(self.message)


class StreetRequired(Exception):
    """Lançada quando o logradouro não é fornecido."""
    def __init__(self, message=None):
        self.message = message or _("Logradouro é obrigatório.")
        super().__init__(self.message)


class NumberRequired(Exception):
    """Lançada quando o número não é fornecido."""
    def __init__(self, message=None):
        self.message = message or _("Número é obrigatório.")
        super().__init__(self.message)


class NeighborhoodRequired(Exception):
    """Lançada quando o bairro não é fornecido."""
    def __init__(self, message=None):
        self.message = message or _("Bairro é obrigatório.")
        super().__init__(self.message)


# ── Exceções de Regras de Negócio ──────────────────────────────────────────

class MultiplePreferentialAddresses(Exception):
    """Lançada quando um cliente tem mais de um endereço preferencial."""
    def __init__(self, message=None):
        self.message = message or _("Cliente não pode ter mais de um endereço preferencial.")
        super().__init__(self.message)


class CannotDeletePreferentialAddress(Exception):
    """Lançada quando tenta deletar o único endereço preferencial."""
    def __init__(self, message=None):
        self.message = message or _("Não é possível deletar o endereço preferencial. Defina outro como preferencial primeiro.")
        super().__init__(self.message)


class AddressLimitExceeded(Exception):
    """Lançada quando o cliente excede o limite de endereços."""
    def __init__(self, message=None, limit=10):
        self.limit = limit
        self.message = message or _(f"Limite máximo de {limit} endereços por cliente atingido.")
        super().__init__(self.message)


class CannotChangeCountry(Exception):
    """Lançada quando tenta alterar o país de um endereço existente."""
    def __init__(self, message=None):
        self.message = message or _("Não é possível alterar o país de um endereço existente.")
        super().__init__(self.message)


class StateMismatch(Exception):
    """Lançada quando o estado não corresponde ao CEP."""
    def __init__(self, message=None):
        self.message = message or _("Estado não corresponde ao CEP informado.")
        super().__init__(self.message)


class CityMismatch(Exception):
    """Lançada quando a cidade não corresponde ao CEP."""
    def __init__(self, message=None):
        self.message = message or _("Cidade não corresponde ao CEP informado.")
        super().__init__(self.message)


# ── Exceções de Permissão ──────────────────────────────────────────────────

class AddressPermissionDenied(Exception):
    """Lançada quando o usuário não tem permissão para acessar/modificar o endereço."""
    def __init__(self, message=None):
        self.message = message or _("Você não tem permissão para acessar este endereço.")
        super().__init__(self.message)


class AddressOwnerMismatch(Exception):
    """Lançada quando o endereço não pertence ao cliente."""
    def __init__(self, message=None):
        self.message = message or _("Este endereço não pertence ao cliente informado.")
        super().__init__(self.message)


# ── Exceções de Conflito ──────────────────────────────────────────────────

class AddressAlreadyExists(Exception):
    """Lançada quando um endereço duplicado é detectado."""
    def __init__(self, message=None):
        self.message = message or _("Endereço já cadastrado para este cliente.")
        super().__init__(self.message)


class DuplicateAddress(Exception):
    """Lançada quando o mesmo endereço é cadastrado múltiplas vezes."""
    def __init__(self, message=None):
        self.message = message or _("Endereço duplicado. Este endereço já está cadastrado.")
        super().__init__(self.message)


# ── Exceções de Formato ────────────────────────────────────────────────────

class InvalidAddressFormat(Exception):
    """Lançada quando o formato do endereço é inválido."""
    def __init__(self, message=None):
        self.message = message or _("Formato de endereço inválido.")
        super().__init__(self.message)


class InvalidNumberFormat(Exception):
    """Lançada quando o número do endereço tem formato inválido."""
    def __init__(self, message=None):
        self.message = message or _("Formato do número inválido. Use apenas números e letras.")
        super().__init__(self.message)


# ── Exceções de Status ─────────────────────────────────────────────────────

class AddressInactive(Exception):
    """Lançada quando tenta operar com um endereço inativo."""
    def __init__(self, message=None):
        self.message = message or _("Endereço inativo. Não é possível realizar esta operação.")
        super().__init__(self.message)


class AddressAlreadyActive(Exception):
    """Lançada quando tenta ativar um endereço já ativo."""
    def __init__(self, message=None):
        self.message = message or _("Endereço já está ativo.")
        super().__init__(self.message)


class AddressAlreadyInactive(Exception):
    """Lançada quando tenta desativar um endereço já inativo."""
    def __init__(self, message=None):
        self.message = message or _("Endereço já está inativo.")
        super().__init__(self.message)