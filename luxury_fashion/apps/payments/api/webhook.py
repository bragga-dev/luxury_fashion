"""
Webhook público da Asaas — quem chama aqui é a Asaas, não um cliente
logado, por isso `auth=None` nessa rota mesmo com a API tendo auth global.
A validação de segurança é o token enviado no header `asaas-access-token`,
configurado no painel da Asaas e comparado com ASAAS_WEBHOOK_TOKEN.
"""
import logging

from ninja import Router

from luxury_fashion.apps.core.exceptions import InvalidWebhookToken
from luxury_fashion.apps.core.schemas.deafult_schema import MessageOut
from luxury_fashion.apps.payments.schemas.payment_schema import AsaasWebhookIn
from luxury_fashion.apps.payments.services.payment_service import handle_asaas_webhook

logger = logging.getLogger(__name__)

router = Router()


@router.post(
    "",
    response={200: MessageOut, 401: MessageOut},
    auth=None,
    summary="Recebe eventos de cobrança da Asaas",
)
def asaas_webhook_router(request, payload: AsaasWebhookIn):
    token = request.headers.get("asaas-access-token", "")
    try:
        handle_asaas_webhook(token=token, event=payload.event, payment_data=payload.payment)
    except InvalidWebhookToken as e:
        logger.warning("Webhook Asaas recusado: token inválido.")
        return 401, {"detail": str(e)}
    except Exception:
        # Nunca deixa a Asaas ficar re-tentando por erro nosso indefinidamente
        # sem log — mas também não expõe detalhe interno pra fora.
        logger.exception("Erro ao processar webhook da Asaas: event=%s", payload.event)

    return 200, {"detail": "ok"}