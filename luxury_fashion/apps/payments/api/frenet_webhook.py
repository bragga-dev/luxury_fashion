"""
Webhooks públicos da Frenet (status e tracking). Quem chama é a Frenet, por isso
`auth=None`; a segurança é o segredo FRENET_WEBHOOK_TOKEN_VALUE, aceito na query string (?token=) ou no header.
Sempre respondemos 2xx para eventos válidos (a Frenet exige resposta em < 10s e
trata 3xx/erro como falha).
"""
import logging
from typing import Optional

from ninja import Router, Schema, Status
from django_ratelimit.decorators import ratelimit

from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.services.frenet_webhook_service import (
    handle_status_update,
    handle_tracking_update,
    is_valid_webhook_token,
)

logger = logging.getLogger(__name__)
router = Router()


class FrenetStatusWebhookIn(Schema):
    OrderId: str
    ShipmentId: int
    ShipmentStatus: int


class FrenetTrackingWebhookIn(Schema):
    OrderId: str
    ShipmentId: int
    TrackingUrl: Optional[str] = None
    TrackingNumber: Optional[str] = None


@router.post("/status", response={200: MessageOut, 401: MessageOut, 500: MessageOut}, auth=None,
             summary="Webhook Frenet — atualização de status do envio")
@ratelimit(key="ip", rate="120/m", block=True)
def frenet_status_webhook(request, payload: FrenetStatusWebhookIn):
    if not is_valid_webhook_token(request.headers, request.GET):
        logger.warning("Webhook Frenet (status) recusado: token inválido.")
        return Status(401, {"detail": "Token inválido."})
    try:
        handle_status_update(payload.OrderId, payload.ShipmentId, payload.ShipmentStatus)
    except Exception:
        logger.exception("Erro no webhook Frenet (status): order=%s", payload.OrderId)
        return Status(500, {"detail": "Erro interno ao processar webhook."})
    return Status(200, {"detail": "ok"})


@router.post("/tracking", response={200: MessageOut, 401: MessageOut, 500: MessageOut}, auth=None,
             summary="Webhook Frenet — atualização de tracking")
@ratelimit(key="ip", rate="120/m", block=True)
def frenet_tracking_webhook(request, payload: FrenetTrackingWebhookIn):
    if not is_valid_webhook_token(request.headers, request.GET):
        logger.warning("Webhook Frenet (tracking) recusado: token inválido.")
        return Status(401, {"detail": "Token inválido."})
    try:
        handle_tracking_update(payload.OrderId, payload.ShipmentId, payload.TrackingNumber)
    except Exception:
        logger.exception("Erro no webhook Frenet (tracking): order=%s", payload.OrderId)
        return Status(500, {"detail": "Erro interno ao processar webhook."})
    return Status(200, {"detail": "ok"})