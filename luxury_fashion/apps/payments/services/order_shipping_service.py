"""
Geração de etiqueta de envio (Frenet Orders OneClick) para um pedido.

Responsabilidades:
- validar pré-condições de negócio (pedido pago, serviço escolhido, sem etiqueta);
- montar o payload do OneClick a partir do Order;
- chamar o FrenetClient (única camada que fala HTTP);
- persistir ShipmentId / LabelUrl / TrackingUrl / status no Order.

Segurança financeira: o OneClick DEBITA a carteira Frenet. O pedido é travado
(select_for_update) durante a chamada e o status só muda após sucesso confirmado,
para impedir compra dupla de etiqueta.
"""
import logging
from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction

from luxury_fashion.apps.core.exceptions.shipping import (
    FrenetLabelError,
    OrderLabelNotAllowed,
)
from luxury_fashion.apps.core.security.cpf_crypto import only_digits
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.products.integrations.frenet_client import FrenetClient

logger = logging.getLogger(__name__)

# Rotas que receberão os webhooks da Frenet (a URL vai em TODO pedido criado;
# não existe cadastro prévio do lado da Frenet).
STATUS_WEBHOOK_PATH = "/api/shipping/webhooks/frenet/status"
TRACKING_WEBHOOK_PATH = "/api/shipping/webhooks/frenet/tracking"


def _money(value: Decimal | float) -> float:
    return round(float(value), 2)


def _f(value) -> float:
    return float(value or 0)


def generate_label_for_order(order_id) -> Order:
    """Gera (e paga) a etiqueta do pedido. Retorna o Order atualizado."""
    with transaction.atomic():
        order = (
            Order.objects.select_for_update(of=("self",))
            .select_related("user_id", "user_id__client_profile", "shipping_address")
            .get(pk=order_id)
        )
        _assert_can_generate(order)
        
        payload = _build_shipment_payload(order)
        result = FrenetClient().create_order_oneclick([payload])
        shipment = _extract_shipment_result(result)

        order.frenet_order_id = str(shipment["shipment_id"])
        order.shipping_label_url = shipment["label_url"]
        order.shipping_tracking_code = shipment["tracking_code"]
        order.shipping_status = Order.ShippingStatus.LABEL_GENERATED
        order.save(
            update_fields=[
                "frenet_order_id",
                "shipping_label_url",
                "shipping_tracking_code",
                "shipping_status",
                "updated_at",
            ]
        )
        logger.info("Etiqueta gerada: order=%s frenet_shipment=%s", order.code, order.frenet_order_id)
        return order


# ─────────────────────────────────────────────────────────────────
# Pré-condições
# ─────────────────────────────────────────────────────────────────

def _assert_can_generate(order: Order) -> None:
    if order.order_status != Order.StatusOrder.COMPLETED:
        raise OrderLabelNotAllowed("Só é possível gerar etiqueta de pedidos pagos (status Completo).")
    if order.shipping_status != Order.ShippingStatus.PENDING or order.frenet_order_id:
        raise OrderLabelNotAllowed("Etiqueta já foi gerada para este pedido.")
    if not order.shipping_service_code:
        raise OrderLabelNotAllowed("Pedido não possui um serviço de frete selecionado.")

    items = list(order.items.select_related("variant_id__product_id", "variant_id__shipping"))
    if not items:
        raise OrderLabelNotAllowed("Pedido sem itens.")
    for item in items:
        if not hasattr(item.variant_id, "shipping"):
            raise OrderLabelNotAllowed(
                f"Variante '{item.variant_id}' sem dados de frete (peso/dimensões)."
            )

    client = getattr(order.user_id, "client_profile", None)
    if client is None or not client.cpf:
        raise OrderLabelNotAllowed("Cliente sem CPF cadastrado — obrigatório para gerar a etiqueta.")
    if not client.phone:
        raise OrderLabelNotAllowed("Cliente sem telefone cadastrado — obrigatório para gerar a etiqueta.")


# ─────────────────────────────────────────────────────────────────
# Payload
# ─────────────────────────────────────────────────────────────────

def _build_shipment_payload(order: Order) -> dict:
    client = order.user_id.client_profile
    addr = order.shipping_address
    items = list(order.items.select_related("variant_id__product_id", "variant_id__shipping"))

    order_items, total_weight, max_len, max_wid, total_height = [], 0.0, 0.0, 0.0, 0.0
    for it in items:
        variant = it.variant_id
        ship = variant.shipping
        qty = it.order_item_quantity
        order_items.append(
            {
                "ItemId": str(it.order_item_id),
                "ProductId": str(variant.variant_id),
                "ProductName": str(variant),
                "Weight": _f(ship.weight),
                "Length": _f(ship.length),
                "Height": _f(ship.height),
                "Width": _f(ship.width),
                "Quantity": qty,
                "Price": _money(it.order_item_price),
            }
        )
        # Heurística de consolidação em 1 volume: peso soma, maior comprimento/largura,
        # alturas empilhadas. Ajuste se passar a embalar itens em caixas separadas.
        total_weight += _f(ship.weight) * qty
        max_len = max(max_len, _f(ship.length))
        max_wid = max(max_wid, _f(ship.width))
        total_height += _f(ship.height) * qty

    phone = client.phone.national_number if hasattr(client.phone, "national_number") else only_digits(str(client.phone))

    shipment = {
        "Order": {
            "Id": order.code,
            "Value": _money(order.total_geral),
            "Created": order.created_at.isoformat(),
            # Conta Frenet do lojista (pessoa física) já tem remetente cadastrado.
            "UseFrenetRegistration": True,
            "Items": order_items,
            "To": {
                "Name": client.get_full_name(),
                "Email": order.user_id.email,
                "Document": only_digits(client.cpf),
                "Cellphone": str(phone),
                "Address": {
                    "ZipCode": only_digits(addr.cep),
                    "Street": addr.street,
                    "AddressNumber": addr.number,
                    "AddressComplement": addr.complement or "",
                    "AddressQuarter": addr.neighborhood,
                    "City": addr.city,
                    "AddressState": addr.state,
                    "Country": "BR",
                },
            },
        },
        "Volumes": {
            "Weight": round(total_weight, 3),
            "Length": max_len,
            "Width": max_wid,
            "Height": round(total_height, 2),
            "Price": _money(order.subtotal),
            "DeclaredValue": _money(order.subtotal),
            "OrderItemsId": [o["ItemId"] for o in order_items],
        },
        "Quotation": {
            "ShippingServiceCode": order.shipping_service_code,
            "PlatformShippingPrice": _money(order.order_shipping_total),
        },
    }

    base = (settings.FRENET_WEBHOOK_BASE_URL or "").rstrip("/")
    if base:
        shipment["StatusNotificationUrl"] = f"{base}{STATUS_WEBHOOK_PATH}"
        shipment["TrackingNotificationUrl"] = f"{base}{TRACKING_WEBHOOK_PATH}"

    return shipment


# ─────────────────────────────────────────────────────────────────
# Resposta
# ─────────────────────────────────────────────────────────────────

def _ci(d: dict, key: str):
    """Lookup case-insensitive: a doc mostra PascalCase no schema e camelCase no exemplo."""
    if not isinstance(d, dict):
        return None
    for k, v in d.items():
        if k.lower() == key.lower():
            return v
    return None


def _extract_shipment_result(result: dict) -> dict:
    items = _ci(result, "Items") or []
    if not items:
        err = _ci(result, "Error") or {}
        raise FrenetLabelError(_ci(err, "Message") or "A Frenet não retornou nenhum envio.", payload=result)

    item = items[0]
    errors = _ci(item, "Errors") or []
    shipment_id = _ci(item, "ShipmentId")
    label_url = _ci(item, "LabelUrl")

    if errors or not shipment_id or not label_url:
        msg = "; ".join(f"[{_ci(e, 'Code')}] {_ci(e, 'Message')}" for e in errors) or "Etiqueta não gerada."
        # Pedido pode ter sido criado na Frenet mesmo sem etiqueta (ex.: 3000 saldo): conferir no painel.
        raise FrenetLabelError(
            f"Frenet não gerou a etiqueta: {msg}" + (f" (ShipmentId {shipment_id} criado no painel)" if shipment_id else ""),
            payload=result,
        )

    return {
        "shipment_id": shipment_id,
        "label_url": label_url,
        "tracking_code": _tracking_code_from_url(_ci(item, "TrackingUrl")),
    }


def _tracking_code_from_url(url: str | None) -> str | None:
    """O OneClick devolve só TrackingUrl (…/COR/PY943133131BR); o código é o último segmento."""
    if not url:
        return None
    segment = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return segment or None