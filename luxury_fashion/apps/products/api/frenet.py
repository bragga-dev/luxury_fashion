"""
Frenet endpoints — cotação de frete por variante.
"""
import uuid

from django_ratelimit.decorators import ratelimit
from ninja import Router
from pydantic import ValidationError as PydanticValidationError

from luxury_fashion.apps.core.exceptions import (
    FrenetAPIError,
    ShippingNotFound,
    VariantNotFound,
)
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.products.schemas.product_shipping_schema import (
    FrenetShippingOptionOut,
    ShippingQuoteIn,
)
from luxury_fashion.apps.products.services.frenet_service import (
    quote_shipping_for_variant,
)

router = Router()


@router.post(
    "/quote/{variant_id}",
    response={200: list[FrenetShippingOptionOut], 400: MessageOut, 404: MessageOut, 502: MessageOut},
    auth=None,
    summary="Cota o frete de uma variante na Frenet",
    description=(
        "Endpoint público. Recebe o CEP de destino (e, opcionalmente, a "
        "quantidade real do carrinho — sobrescreve a quantidade padrão de "
        "embalagem cadastrada) e retorna as opções de frete disponíveis "
        "para essa variante, na ordem devolvida pela Frenet."
    ),
)
@ratelimit(key="ip", rate="30/m", block=True)
def quote_shipping_router(request, variant_id: uuid.UUID, payload: ShippingQuoteIn):
    try:
        options = quote_shipping_for_variant(variant_id, payload)
        return 200, options
    except VariantNotFound as e:
        return 404, {"detail": str(e)}
    except ShippingNotFound as e:
        return 404, {"detail": str(e)}
    except FrenetAPIError as e:
        return 502, {"detail": str(e)}
    except PydanticValidationError as e:
        return 400, {"detail": str(e)}