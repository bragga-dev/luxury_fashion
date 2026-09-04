import hashlib
import hmac
import re

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _fernet() -> Fernet:
    key = settings.CPF_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_cpf(cpf: str) -> str:
    return _fernet().encrypt(cpf.encode()).decode()


def decrypt_cpf(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValidationError(_("Não foi possível decifrar o CPF armazenado."))


def hash_cpf(cpf: str) -> str:
    key = settings.CPF_HASH_KEY
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, cpf.encode(), hashlib.sha256).hexdigest()