import re

import brazilcep
from brazilcep.exceptions import (
    BlockedByFlood,
    CEPNotFound,
    ConnectionError as BrazilCEPConnectionError,
    HTTPError,
    InvalidCEP,
    Timeout,
    BrazilCEPException,
)

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_cep(value):
    """
    Valida o formato do CEP e verifica se ele existe
    através de uma consulta ao serviço de CEP.
    """

    cep = re.sub(r"\D", "", value)

    if len(cep) != 8:
        raise ValidationError(
            _("O CEP deve possuir 8 dígitos.")
        )

    try:
        address = brazilcep.get_address_from_cep(cep)

    except (InvalidCEP, CEPNotFound):
        raise ValidationError(
            _("O CEP informado não existe.")
        )
    except (BlockedByFlood, BrazilCEPConnectionError, HTTPError, Timeout):
        raise ValidationError(
            _("Não foi possível consultar o CEP no momento. Tente novamente mais tarde.")
        )
    except BrazilCEPException:
        raise ValidationError(
            _("Não foi possível consultar o CEP.")
        )

    if not address:
        raise ValidationError(
            _("O CEP informado não existe.")
        )

    return cep