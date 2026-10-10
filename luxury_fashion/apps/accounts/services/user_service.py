"""
User Services — criação e atualização de usuário base.
"""
import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from luxury_fashion.apps.accounts.models.client_model import Client
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.repositories.client_repository import (
    create_client,
    delete_client,
    remove_client_photo,
    update_client,
)
from luxury_fashion.apps.cart.repositories.cart_repository import create_cart

from luxury_fashion.apps.accounts.repositories.user_repository import (
    activate_user,
    create_user,
    delete_user,
    record_terms_acceptance,
    set_marketing_opt_in,
)
from luxury_fashion.apps.accounts.schemas.me_schema import (
    MeOut,

    )
from luxury_fashion.apps.accounts.schemas.user_schema import ConsentOut, ConsentUpdateIn, RegisterIn
from luxury_fashion.apps.accounts.schemas.client_schema import ClientUpdateIn, ClientOut
from luxury_fashion.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,
)
from luxury_fashion.apps.accounts.selectors.user_selector import (
    email_exists,
    filter_users_admin,
    get_user_by_email,
    get_user_by_id,
    get_user_confirmed_by_role,
    get_user_with_related,
)

from luxury_fashion.apps.accounts.tasks.verification_account import (
    send_verification_email,
)
from luxury_fashion.apps.core.exceptions.permissions import PermissionDenied
from luxury_fashion.apps.core.exceptions.auth import InvalidGoogleToken, InvalidPassword, TermsNotAccepted
from luxury_fashion.apps.core.exceptions.user import UserAlreadyExists


from luxury_fashion.apps.core.exceptions.user import UserNotFound
from luxury_fashion.apps.core.oauth.google import verify_google_id_token
from luxury_fashion.apps.core.tokens.jwt import make_tokens, revoke_all_tokens

logger = logging.getLogger(__name__)



def get_current_user_profile(user_id: uuid.UUID) -> MeOut:
   
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")
    return MeOut.from_user(user)


def update_client_profile(user_id: uuid.UUID, payload: ClientUpdateIn) -> ClientOut:
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    if user.role != User.UserRole.CLIENT:
        raise PermissionDenied("Apenas clientes podem atualizar este perfil.")

    fields = payload.dict(exclude_unset=True)
    updated_client = update_client(client=user.client_profile, **fields)
    return ClientOut.from_orm(updated_client)



def _record_consents(user: User, *, accepted_terms: bool, marketing_opt_in: bool, ip: str | None) -> None:
    if accepted_terms:
        record_terms_acceptance(
            user,
            terms_version=settings.LEGAL_TERMS_VERSION,
            privacy_version=settings.LEGAL_PRIVACY_VERSION,
            ip=ip,
        )
    if marketing_opt_in:
        set_marketing_opt_in(user, True)


def _consent_out(user: User) -> ConsentOut:
    needs = (
        user.terms_version != settings.LEGAL_TERMS_VERSION
        or user.privacy_version != settings.LEGAL_PRIVACY_VERSION
    )
    return ConsentOut(
        terms_accepted=bool(user.terms_accepted_at),
        terms_version_accepted=user.terms_version,
        privacy_version_accepted=user.privacy_version,
        terms_accepted_at=user.terms_accepted_at,
        current_terms_version=settings.LEGAL_TERMS_VERSION,
        current_privacy_version=settings.LEGAL_PRIVACY_VERSION,
        needs_reacceptance=needs,
        marketing_opt_in=user.marketing_opt_in,
        marketing_opt_in_at=user.marketing_opt_in_at,
    )


def get_consents(user: User) -> ConsentOut:
    return _consent_out(user)


def update_consents(user: User, data: ConsentUpdateIn, ip: str | None = None) -> ConsentOut:
    """Aceite de uma nova versão dos termos (ou do primeiro aceite, p/ contas antigas) e opt-in/out de marketing."""
    if data.accepted_terms:
        record_terms_acceptance(
            user,
            terms_version=settings.LEGAL_TERMS_VERSION,
            privacy_version=settings.LEGAL_PRIVACY_VERSION,
            ip=ip,
        )
    if data.marketing_opt_in is not None and data.marketing_opt_in != user.marketing_opt_in:
        set_marketing_opt_in(user, data.marketing_opt_in)
    return _consent_out(user)


@transaction.atomic
def register_user_default_client(data: RegisterIn, user_agent: str = "", ip: str | None = None) -> dict:
    """
    Cria o User + Client e dispara e-mail de verificação.
    Retorna os tokens JWT diretamente para o cliente já poder operar.
    """
    if email_exists(data.email):
        raise UserAlreadyExists("e-mail")
    user = create_user(email=data.email, password=data.password, role=User.UserRole.CLIENT)
    _record_consents(user, accepted_terms=data.accepted_terms, marketing_opt_in=data.marketing_opt_in, ip=ip)

    if user.role == User.UserRole.CLIENT:
        create_client(user)
        create_cart(user)

    send_verification_email.delay(user.pk)   
    return make_tokens(user, user_agent=user_agent)


@transaction.atomic
def login_or_register_client_google(
    id_token: str,
    user_agent: str = "",
    accepted_terms: bool = False,
    marketing_opt_in: bool = False,
    ip: str | None = None,
) -> tuple[dict, bool]:
    """
    Login/Cadastro de Cliente via Google (Sign in with Google).

    - Valida o id_token junto ao Google (assinatura, expiração, audience).
    - Se já existe um usuário com o e-mail do token: apenas loga (e ativa
      a conta, caso ainda não estivesse ativa — o Google já garante que
      o e-mail é verificado).
    - Se não existe: cria um Cliente novo, já ativo, sem senha utilizável
      (login exclusivamente via Google até que o usuário defina uma senha).

    Retorna (tokens, created) — created=True quando um novo usuário foi criado,
    útil para o endpoint decidir entre 200 (login) e 201 (cadastro).
    """
    claims = verify_google_id_token(id_token)

    if not claims.get("email_verified", False):
        raise InvalidGoogleToken("E-mail da conta Google não verificado.")

    email = claims["email"]
    user = get_user_by_email(email)
    created = False

    if user is None:
        # Conta nova = precisa de aceite explícito dos termos (o front mostra o checkbox e reenvia).
        if not accepted_terms:
            raise TermsNotAccepted()
        user = create_user(email=email, password=None, role=User.UserRole.CLIENT)
        _record_consents(user, accepted_terms=True, marketing_opt_in=marketing_opt_in, ip=ip)
        create_client(
            user,
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
        )
        create_cart(user)
        created = True

    if not user.is_active or not user.is_trusty:
        user = activate_user(user)

    return make_tokens(user, user_agent=user_agent), created




@transaction.atomic
def deactivate_account(user_id: uuid.UUID, performed_by=None, reason="Desativação de conta"):
    """ Desativa usuário, revoga todos os tokens ativos e cria log de auditoria"""
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Desativação abortada: usuário {user_id} não encontrado")
        raise UserNotFound("Usuário não encontrado.")
 
    if not user.is_active:
        logger.warning(f"Desativação abortada: usuário {user_id} já está inativo")
        raise UserNotFound("Usuário já está desativado.")
 
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
 
    user.is_active = False
    user.save(update_fields=["is_active"])
 
    return user


def reactivate_user(user_id: uuid.UUID, performed_by=None) -> User:
    """Contrapartida de deactivate_account: reativa um usuário desativado. Restrito a admin."""
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Reativação abortada: usuário {user_id} não encontrado")
        raise UserNotFound("Usuário não encontrado.")

    if user.is_active:
        logger.warning(f"Reativação abortada: usuário {user_id} já está ativo")
        raise UserNotFound("Usuário já está ativo.")

    return activate_user(user)


@transaction.atomic
def delete_own_account(user: User, password: str) -> None:
    """
    Exclusão de conta pelo próprio usuário (LGPD — direito de eliminação).

    - Cliente SEM pedidos: exclusão definitiva (User, perfil, endereços, carrinho, avaliações).
    - Cliente COM pedidos: o registro do User e os pedidos/pagamentos/endereços de entrega usados
      neles são mantidos — são dados fiscais e comerciais que a lei obriga a guardar (LGPD art. 16, I;
      prazo tributário de 5 anos) e as FKs são PROTECT. Todo o resto vira anonimizado/apagado:
      e-mail, nome, telefone, nascimento, CPF, foto, endereços sem pedido, carrinho, avaliações e
      mensagens de contato. A senha fica inutilizável e as sessões são revogadas.

    Em ambos os casos apaga também as mensagens do formulário de contato feitas com o e-mail da conta.
    Contas admin não podem ser excluídas por aqui.
    """
    from luxury_fashion.apps.cart.models.cart_model import Cart
    from luxury_fashion.apps.payments.models.order_model import Order
    from luxury_fashion.apps.reviews.models.reviews_model import Reviews
    from luxury_fashion.apps.website.models.contact_model import Contact

    if user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Contas de administrador não podem ser excluídas por este endpoint.")

    if not user.check_password(password):
        raise InvalidPassword("Senha incorreta. Não foi possível confirmar a exclusão da conta.")

    original_email = user.email
    revoke_all_tokens(user)
    Contact.objects.filter(email__iexact=original_email).delete()

    profile = getattr(user, "client_profile", None) if user.role == User.UserRole.CLIENT else None
    if profile is not None:
        remove_client_photo(profile)  # volta pra foto padrão (NUNCA apaga a padrão compartilhada)

    if not Order.objects.filter(user_id=user).exists():
        delete_user(user)
        return

    # ── tem pedidos: anonimiza e mantém só o necessário ──
    Reviews.objects.filter(user_id=user).delete()
    Cart.objects.filter(user_id=user).delete()

    if profile is not None:
        profile.addresses.filter(orders__isnull=True).delete()
        profile.first_name = None
        profile.last_name = None
        profile.username = None
        profile.phone = None
        profile.gender = Client._meta.get_field("gender").default
        profile.birth_date = None
        profile.cpf = None
        profile.save()

    user.email = f"anonimizado-{user.user_id}@excluido.invalid"
    user.set_unusable_password()
    user.is_active = False
    user.is_trusty = False
    user.marketing_opt_in = False
    user.consent_ip = None
    user.save()


def export_user_data(user_id: uuid.UUID) -> dict:
    """
    Export dos dados pessoais do usuário (LGPD — direito de acesso e portabilidade): conta e
    consentimentos, perfil, endereços, pedidos (itens, frete, pagamentos), avaliações e mensagens
    enviadas pelo formulário de contato.
    """
    from luxury_fashion.apps.payments.models.order_model import Order
    from luxury_fashion.apps.reviews.models.reviews_model import Reviews
    from luxury_fashion.apps.website.models.contact_model import Contact

    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    def iso(value):
        return value.isoformat() if value else None

    data = {
        "conta": {
            "id": str(user.user_id),
            "email": user.email,
            "tipo": user.get_role_display(),
            "ativo": user.is_active,
            "confiavel": user.is_trusty,
            "data_cadastro": iso(user.date_joined),
            "criado_em": iso(user.created_at),
            "atualizado_em": iso(user.updated_at),
        },
        "consentimentos": {
            "termos_aceitos_em": iso(user.terms_accepted_at),
            "versao_termos": user.terms_version or None,
            "versao_politica_privacidade": user.privacy_version or None,
            "ip_do_aceite": user.consent_ip,
            "aceita_marketing": user.marketing_opt_in,
            "marketing_alterado_em": iso(user.marketing_opt_in_at),
        },
        "perfil": None,
        "enderecos": [],
        "pedidos": [],
        "avaliacoes": [],
        "mensagens_de_contato": [],
    }

    profile = getattr(user, "client_profile", None) if user.role == User.UserRole.CLIENT else None
    if profile:
        data["perfil"] = {
            "nome": profile.first_name,
            "sobrenome": profile.last_name,
            "username": profile.username,
            "telefone": str(profile.phone) if profile.phone else None,
            "genero": profile.gender,
            "data_nascimento": iso(profile.birth_date),
            "cpf": profile.cpf,
            "foto_url": profile.photo_url,
        }
        data["enderecos"] = [
            {
                "id": str(a.address_id),
                "cep": a.cep,
                "logradouro": a.street,
                "numero": a.number,
                "complemento": a.complement,
                "bairro": a.neighborhood,
                "cidade": a.city,
                "estado": a.state,
                "pais": a.country,
                "preferencial": a.is_preferential,
            }
            for a in profile.addresses.all()
        ]

    orders = (
        Order.objects.filter(user_id=user)
        .select_related("shipping_address")
        .prefetch_related("items__variant_id__product_id", "payments")
        .order_by("created_at")
    )
    for o in orders:
        addr = o.shipping_address
        data["pedidos"].append({
            "codigo": o.code,
            "status": o.order_status,
            "criado_em": iso(o.created_at),
            "subtotal": str(o.subtotal),
            "frete": str(o.order_shipping_total),
            "total": str(o.total_geral),
            "servico_de_frete": o.shipping_service_name,
            "prazo_prometido_dias": o.shipping_delivery_days,
            "codigo_de_rastreio": o.shipping_tracking_code,
            "status_do_envio": o.shipping_status,
            "endereco_de_entrega": {
                "cep": addr.cep, "logradouro": addr.street, "numero": addr.number,
                "complemento": addr.complement, "bairro": addr.neighborhood,
                "cidade": addr.city, "estado": addr.state,
            },
            "itens": [
                {
                    "produto": str(i.variant_id),
                    "quantidade": i.order_item_quantity,
                    "preco_unitario": str(i.order_item_price),
                }
                for i in o.items.all()
            ],
            "pagamentos": [
                {
                    "forma": p.billing_type,
                    "status": p.status,
                    "valor": str(p.value),
                    "criado_em": iso(p.created_at),
                }
                for p in o.payments.all()
            ],
        })

    data["avaliacoes"] = [
        {"nota": r.reviews, "comentario": r.comment, "criado_em": iso(r.created_at)}
        for r in Reviews.objects.filter(user_id=user).order_by("created_at")
    ]
    data["mensagens_de_contato"] = [
        {
            "assunto": c.subject,
            "mensagem": c.message,
            "telefone": c.phone,
            "status": c.status,
            "criado_em": iso(c.created_at),
        }
        for c in Contact.objects.filter(email__iexact=user.email).order_by("created_at")
    ]

    data["gerado_em"] = timezone.now().isoformat()
    return data


# ── Admin: listagem ──────────────────────────────────────────────────────────

def list_users_admin(search: str = None, role: str = None, is_active: bool = None):
    """
    Lista usuários para o painel admin com filtros combináveis.
    Retorna QuerySet pronto para paginação na camada de router.
    """
    return filter_users_admin(search=search, role=role, is_active=is_active)