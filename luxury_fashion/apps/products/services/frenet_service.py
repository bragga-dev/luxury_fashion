"""
Frenet Service — orquestra a cotação de frete de uma variante de produto
usando a API da Frenet.

Une duas peças que não se conhecem:
- os dados físicos (peso/dimensões/CEP de origem) já cadastrados em
  ProductShipping (ver product_shipping_service);
- o FrenetClient, wrapper fino sem regra nenhuma sobre a API da Frenet.

Nenhuma chamada HTTP acontece fora do FrenetClient, e nenhuma regra de
negócio (qual quantidade usar, como montar o valor da nota, como
interpretar a resposta) acontece fora daqui.
"""
import uuid
from decimal import Decimal
from typing import List

from luxury_fashion.apps.core.exceptions import ShippingNotFound, VariantNotFound
from luxury_fashion.apps.products.integrations.frenet_client import FrenetClient
from luxury_fashion.apps.products.schemas.product_shipping_schema import (
    FrenetShippingOptionOut,
    ShippingQuoteIn,
)
from luxury_fashion.apps.products.selectors.product_shipping_selector import (
    get_shipping_by_variant,
)
from luxury_fashion.apps.products.selectors.product_variant_selector import (
    get_variant_by_id,
)


def quote_shipping_for_variant(variant_id: uuid.UUID, data: ShippingQuoteIn)-> List[FrenetShippingOptionOut]:
    """
    Cota o frete de uma variante na Frenet a partir do CEP de destino informado.

    `data.quantity`, quando informado, sobrescreve a quantidade padrão de
    embalagem cadastrada em ProductShipping — é isso que o checkout deve
    mandar (quantidade real no carrinho), não o valor default do cadastro
    do produto. O valor declarado à Frenet (`invoice_value`) é sempre
    recalculado como `preço da variante × quantidade`, nunca cadastrado
    manualmente, pra não ficar dessincronizado do preço real cobrado.
    """
    variant = get_variant_by_id(variant_id)
    if variant is None:
        raise VariantNotFound()

    shipping = get_shipping_by_variant(variant_id)
    if shipping is None:
        raise ShippingNotFound()

    quantity = data.quantity or shipping.quantity
    invoice_value = variant.price * quantity

    response = FrenetClient().calculate_shipping(
        seller_cep=shipping.origin_zip_code,
        recipient_cep=data.recipient_cep,
        weight=shipping.weight,
        height=shipping.height,
        width=shipping.width,
        length=shipping.length,
        invoice_value=invoice_value,
        quantity=quantity,
    )

    return _parse_quote_response(response)


def _parse_quote_response(response: dict) -> List[FrenetShippingOptionOut]:
    """
    Traduz o `ShippingSevicesArray` (nome com o typo que a própria API da
    Frenet usa) em opções utilizáveis pelo front.

    Serviços que a Frenet retornou com erro (ex.: transportadora sem
    cobertura pro CEP, peso acima do limite daquele serviço) não são
    descartados aqui — vêm marcados com `error=True` e a mensagem original,
    pra decisão de exibir ou não ficar com quem consome a cotação.
    """
    options = response.get("ShippingSevicesArray") or []

    parsed: List[FrenetShippingOptionOut] = []
    for option in options:
        has_error = bool(option.get("Error"))
        raw_price = option.get("ShippingPrice")

        parsed.append(
            FrenetShippingOptionOut(
                carrier=option.get("Carrier", ""),
                service=option.get("ServiceDescription", ""),
                service_code=option.get("ServiceCode"),
                price=Decimal(str(raw_price)) if raw_price not in (None, "") else Decimal("0"),
                delivery_time_days=int(option.get("DeliveryTime") or 0),
                error=has_error,
                error_message=option.get("Msg") if has_error else None,
            )
        )
    return parsed
