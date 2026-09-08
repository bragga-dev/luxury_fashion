"""
Webhook público da Asaas — quem chama aqui é a Asaas, não um cliente
logado, por isso `auth=None` nessa rota mesmo com a API tendo auth global.
A validação de segurança é o token enviado no header `asaas-access-token`,
configurado no painel da Asaas e comparado com ASAAS_WEBHOOK_TOKEN.
"""
import logging

from ninja import Router
from django.conf import settings
from luxury_fashion.apps.core.exceptions import InvalidWebhookToken
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.schemas.payment_schema import AsaasWebhookIn
from luxury_fashion.apps.payments.services.payment_service import handle_asaas_webhook
from django.http import HttpRequest
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)

router = Router()


@router.post(
    "/webhook",
    response={200: MessageOut, 401: MessageOut, 500: MessageOut},
    auth=None,
    summary="Recebe eventos de cobrança da Asaas",
)
@ratelimit(key="ip", rate="60/m", block=True)
def asaas_webhook_router(request, payload: AsaasWebhookIn):
    token = request.headers.get("asaas-access-token", "")
    try:
        handle_asaas_webhook(
            token=token,
            event=payload.event,
            payment_data=payload.payment,
        )

    except InvalidWebhookToken as e:
        logger.warning("Webhook Asaas recusado: token inválido.")
        return 401, {"detail": str(e)}
    except Exception:
        logger.exception("Erro ao processar webhook da Asaas: event=%s", payload.event)
        return 500, {"detail": "Erro interno ao processar webhook."}

    return 200, {"detail": "ok"}