"""
Testes da geração de etiqueta (Frenet OneClick). Nenhuma chamada HTTP real:
`requests.Session.request` é mockado, então nenhum saldo é gasto.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import requests

from luxury_fashion.apps.core.exceptions.shipping import (
    FrenetInsufficientBalanceError,
    FrenetLabelError,
    FrenetPartnerTokenMissingError,
    OrderLabelNotAllowed,
)
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.payments.models.order_model import Order
from luxury_fashion.apps.payments.services.order_shipping_service import (
    _tracking_code_from_url,
    generate_label_for_order,
)
from luxury_fashion.apps.products.models.product_shipping_model import ProductShipping


@pytest.fixture(autouse=True)
def frenet_settings(settings):
    settings.FRENET_PARTNER_TOKEN = "partner-token-teste"
    settings.FRENET_API_KEY = "client-token-teste"
    settings.FRENET_WHITELABEL_BASE_URL = "https://whitelabel.apifrenet.com.br"
    settings.FRENET_WEBHOOK_BASE_URL = "https://api.loja.test"
    settings.FRENET_PRINTING_FORMAT = ""


@pytest.fixture
def paid_order(order, variant, client_profile):
    client_profile.phone = "+5573999998888"
    client_profile.save()
    ProductShipping.objects.create(
        variant_id=variant, weight=Decimal("0.3"), height=Decimal("5"),
        width=Decimal("12"), length=Decimal("16"), quantity=1,
    )
    OrderItem.objects.create(
        order_id=order, variant_id=variant, order_item_quantity=2,
        order_item_price=Decimal("99.95"),
    )
    order.shipping_service_code = "04510"
    order.order_status = Order.StatusOrder.COMPLETED
    order.save()
    return order


def _fake_response(status=200, json_body=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.ok = 200 <= status < 300
    resp.json.return_value = json_body
    resp.text = str(json_body)
    resp.content = b"x"
    return resp


OK_BODY = {
    "StatusBatch": "Processado",
    "Items": [{
        "ShipmentId": 12682,
        "OrderId": "X",
        "ShipmentStatus": 4,
        "TrackingUrl": "https://rastreio.frenet.com.br/COR/PY943133131BR",
        "LabelUrl": "https://painel.frenet.com.br/PrintPreviewCart/Label?shippingOrderId=12682",
        "Errors": None,
    }],
}


@pytest.fixture
def mock_http(monkeypatch):
    m = MagicMock(return_value=_fake_response(200, OK_BODY))
    monkeypatch.setattr(requests.Session, "request", m)
    return m


@pytest.mark.django_db
def test_gera_etiqueta_e_persiste(paid_order, client_profile, mock_http):
    order = generate_label_for_order(paid_order.order_id)

    assert order.shipping_status == Order.ShippingStatus.LABEL_GENERATED
    assert order.frenet_order_id == "12682"
    assert order.shipping_tracking_code == "PY943133131BR"
    assert "shippingOrderId=12682" in order.shipping_label_url

    args, kwargs = mock_http.call_args
    assert args[0] == "POST"
    assert args[1] == "https://whitelabel.apifrenet.com.br/v1/orders/oneclick"
    assert kwargs["headers"]["x-partner-token"] == "partner-token-teste"
    assert "x-printing-format" not in kwargs["headers"]

    body = kwargs["json"]
    assert isinstance(body, list) and len(body) == 1
    s = body[0]
    assert s["Order"]["Id"] == order.code
    assert s["Order"]["To"]["Document"] == "39053344705"
    assert s["Order"]["To"]["Address"]["ZipCode"] == "45200000"
    assert s["Order"]["To"]["Address"]["AddressState"] == "BA"
    assert s["Quotation"]["ShippingServiceCode"] == "04510"
    # 2 un x 0.3kg
    assert s["Volumes"]["Weight"] == 0.6
    assert s["StatusNotificationUrl"].startswith("https://api.loja.test")
    assert s["TrackingNotificationUrl"].startswith("https://api.loja.test")


@pytest.mark.django_db
def test_nao_gera_duas_vezes(paid_order, client_profile, mock_http):
    generate_label_for_order(paid_order.order_id)
    with pytest.raises(OrderLabelNotAllowed):
        generate_label_for_order(paid_order.order_id)
    assert mock_http.call_count == 1


@pytest.mark.django_db
def test_exige_pedido_pago(paid_order, client_profile, mock_http):
    paid_order.order_status = Order.StatusOrder.PENDING
    paid_order.save()
    with pytest.raises(OrderLabelNotAllowed):
        generate_label_for_order(paid_order.order_id)
    mock_http.assert_not_called()


@pytest.mark.django_db
def test_exige_telefone(paid_order, client_profile, mock_http):
    client_profile.phone = ""
    client_profile.save()
    with pytest.raises(OrderLabelNotAllowed, match="telefone"):
        generate_label_for_order(paid_order.order_id)
    mock_http.assert_not_called()


@pytest.mark.django_db
def test_sem_partner_token(paid_order, client_profile, mock_http, settings):
    settings.FRENET_PARTNER_TOKEN = ""
    with pytest.raises(FrenetPartnerTokenMissingError):
        generate_label_for_order(paid_order.order_id)
    mock_http.assert_not_called()


@pytest.mark.django_db
def test_saldo_insuficiente(paid_order, client_profile, mock_http):
    mock_http.return_value = _fake_response(
        400, {"Message": "Erro", "Details": [{"Code": 3000, "Message": "Saldo insuficiente."}]}
    )
    with pytest.raises(FrenetInsufficientBalanceError):
        generate_label_for_order(paid_order.order_id)
    paid_order.refresh_from_db()
    assert paid_order.shipping_status == Order.ShippingStatus.PENDING
    assert paid_order.frenet_order_id is None


@pytest.mark.django_db
def test_erro_por_item_nao_marca_como_gerada(paid_order, client_profile, mock_http):
    mock_http.return_value = _fake_response(200, {
        "StatusBatch": "Erro",
        "Items": [{"ShipmentId": 99, "Errors": [{"Code": 3000, "Message": "Saldo insuficiente."}]}],
    })
    with pytest.raises(FrenetLabelError, match="99"):
        generate_label_for_order(paid_order.order_id)
    paid_order.refresh_from_db()
    assert paid_order.shipping_status == Order.ShippingStatus.PENDING


def test_tracking_code_from_url():
    assert _tracking_code_from_url("http://x/COR/PY1BR") == "PY1BR"
    assert _tracking_code_from_url(None) is None


# ───────────────────────── webhooks ─────────────────────────

@pytest.fixture
def shipped_order(paid_order, mock_http):
    return generate_label_for_order(paid_order.order_id)


@pytest.mark.django_db
def test_webhook_status_postado(client, shipped_order):
    resp = client.post("/api/shipping/webhooks/frenet/status",
                       data={"OrderId": shipped_order.code, "ShipmentId": 12682, "ShipmentStatus": 5},
                       content_type="application/json")
    assert resp.status_code == 200
    shipped_order.refresh_from_db()
    assert shipped_order.shipping_status == Order.ShippingStatus.SHIPPED
    assert shipped_order.shipped_at is not None


@pytest.mark.django_db
def test_webhook_status_cancelado_libera_nova_etiqueta(client, shipped_order):
    client.post("/api/shipping/webhooks/frenet/status",
                data={"OrderId": shipped_order.code, "ShipmentId": 12682, "ShipmentStatus": 7},
                content_type="application/json")
    shipped_order.refresh_from_db()
    assert shipped_order.shipping_status == Order.ShippingStatus.PENDING
    assert shipped_order.frenet_order_id is None


@pytest.mark.django_db
def test_webhook_shipment_id_divergente_ignora(client, shipped_order):
    client.post("/api/shipping/webhooks/frenet/status",
                data={"OrderId": shipped_order.code, "ShipmentId": 999, "ShipmentStatus": 5},
                content_type="application/json")
    shipped_order.refresh_from_db()
    assert shipped_order.shipping_status == Order.ShippingStatus.LABEL_GENERATED


@pytest.mark.django_db
def test_webhook_token_obrigatorio_quando_configurado(client, shipped_order, settings):
    settings.FRENET_WEBHOOK_TOKEN_VALUE = "segredo"
    body = {"OrderId": shipped_order.code, "ShipmentId": 12682, "TrackingNumber": "AB123BR"}
    assert client.post("/api/shipping/webhooks/frenet/tracking", data=body,
                       content_type="application/json").status_code == 401
    ok = client.post("/api/shipping/webhooks/frenet/tracking", data=body,
                     content_type="application/json", HTTP_FRENET_INTEGRATION="segredo")
    assert ok.status_code == 200
    shipped_order.refresh_from_db()
    assert shipped_order.shipping_tracking_code == "AB123BR"


@pytest.mark.django_db
def test_webhook_pedido_desconhecido_retorna_200(client):
    resp = client.post("/api/shipping/webhooks/frenet/status",
                       data={"OrderId": "NAOEXISTE", "ShipmentId": 1, "ShipmentStatus": 5},
                       content_type="application/json")
    assert resp.status_code == 200