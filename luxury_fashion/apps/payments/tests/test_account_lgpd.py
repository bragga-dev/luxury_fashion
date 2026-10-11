"""LGPD: aceite de termos, marketing opt-in, exclusão (anonimização) e export de dados."""
import pytest
from ninja_jwt.tokens import RefreshToken

from luxury_fashion.apps.accounts.models.addresses_client_model import AddressesClient
from luxury_fashion.apps.accounts.models.client_model import DEFAULT_CLIENT_PHOTO
from luxury_fashion.apps.accounts.models.user_model import User
from luxury_fashion.apps.accounts.services import user_service
from luxury_fashion.apps.payments.models.order_item_model import OrderItem
from luxury_fashion.apps.reviews.models.reviews_model import Reviews
from luxury_fashion.apps.website.models.contact_model import Contact

pytestmark = pytest.mark.django_db

SENHA = "Senha-Forte-2026!x"


def auth_header(user) -> dict:
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _sem_email(monkeypatch):
    monkeypatch.setattr(user_service.send_verification_email, "delay", lambda *a, **k: None)


def _register(client, **over):
    body = {"email": "novo@example.com", "password": SENHA, "password2": SENHA, "accepted_terms": True}
    body.update(over)
    return client.post("/api/auth/register", data=body, content_type="application/json", REMOTE_ADDR="203.0.113.7")


# ── cadastro ─────────────────────────────────────────────────────────────

def test_cadastro_sem_aceitar_termos_e_recusado(client):
    assert _register(client, accepted_terms=False).status_code == 422
    assert User.objects.filter(email="novo@example.com").count() == 0


def test_cadastro_sem_o_campo_de_aceite_e_recusado(client):
    body = {"email": "novo@example.com", "password": SENHA, "password2": SENHA}
    resp = client.post("/api/auth/register", data=body, content_type="application/json")
    assert resp.status_code == 422


def test_cadastro_registra_versao_data_e_ip_do_aceite(client, settings):
    settings.LEGAL_TERMS_VERSION = "2.0"
    settings.LEGAL_PRIVACY_VERSION = "3.1"
    resp = _register(client)
    assert resp.status_code == 201, resp.content

    user = User.objects.get(email="novo@example.com")
    assert user.terms_accepted_at is not None
    assert (user.terms_version, user.privacy_version) == ("2.0", "3.1")
    assert user.consent_ip == "203.0.113.7"
    assert user.marketing_opt_in is False  # marketing nunca é presumido


def test_marketing_so_liga_se_o_usuario_pedir(client):
    _register(client, email="m@example.com", marketing_opt_in=True)
    assert User.objects.get(email="m@example.com").marketing_opt_in is True


# ── login com Google ─────────────────────────────────────────────────────

@pytest.fixture
def google(monkeypatch):
    monkeypatch.setattr(
        user_service, "verify_google_id_token",
        lambda token: {"email": "g@example.com", "email_verified": True, "given_name": "Gi", "family_name": "Lo"},
    )


def test_google_conta_nova_sem_aceite_da_400(client, google):
    resp = client.post("/api/auth/google", data={"id_token": "x" * 20}, content_type="application/json")
    assert resp.status_code == 400
    assert not User.objects.filter(email="g@example.com").exists()


def test_google_conta_nova_com_aceite_registra_consentimento(client, google):
    resp = client.post("/api/auth/google", data={"id_token": "x" * 20, "accepted_terms": True},
                       content_type="application/json")
    assert resp.status_code == 201
    assert User.objects.get(email="g@example.com").terms_accepted_at is not None


def test_google_conta_existente_entra_sem_reenviar_aceite(client, google):
    client.post("/api/auth/google", data={"id_token": "x" * 20, "accepted_terms": True}, content_type="application/json")
    resp = client.post("/api/auth/google", data={"id_token": "x" * 20}, content_type="application/json")
    assert resp.status_code == 200


# ── /auth/consents ───────────────────────────────────────────────────────

def test_conta_antiga_precisa_aceitar_e_depois_nao_precisa(client, user, client_profile):
    resp = client.get("/api/auth/consents", **auth_header(user))
    assert resp.status_code == 200
    assert resp.json()["needs_reacceptance"] is True

    resp = client.patch("/api/auth/consents", data={"accepted_terms": True}, content_type="application/json", **auth_header(user))
    assert resp.status_code == 200
    assert resp.json()["needs_reacceptance"] is False
    assert resp.json()["terms_accepted"] is True


def test_nova_versao_dos_termos_exige_novo_aceite(client, user, client_profile, settings):
    client.patch("/api/auth/consents", data={"accepted_terms": True}, content_type="application/json", **auth_header(user))
    settings.LEGAL_TERMS_VERSION = "9.9"
    assert client.get("/api/auth/consents", **auth_header(user)).json()["needs_reacceptance"] is True


def test_marketing_liga_e_desliga(client, user, client_profile):
    on = client.patch("/api/auth/consents", data={"marketing_opt_in": True}, content_type="application/json", **auth_header(user))
    assert on.json()["marketing_opt_in"] is True
    off = client.patch("/api/auth/consents", data={"marketing_opt_in": False}, content_type="application/json", **auth_header(user))
    assert off.json()["marketing_opt_in"] is False
    assert off.json()["marketing_opt_in_at"] is not None


def test_nao_revoga_aceite_dos_termos_por_la(client, user, client_profile):
    resp = client.patch("/api/auth/consents", data={"accepted_terms": False}, content_type="application/json", **auth_header(user))
    assert resp.status_code == 422


# ── exclusão de conta ────────────────────────────────────────────────────

def _delete(client, user, senha="senha-super-segura-123"):
    return client.delete("/api/auth/delete-account", data={"password": senha}, content_type="application/json", **auth_header(user))


def test_exclusao_com_senha_errada_nao_apaga_nada(client, user, client_profile):
    assert _delete(client, user, senha="errada").status_code == 400
    assert User.objects.filter(pk=user.pk).exists()


def test_exclusao_sem_pedidos_apaga_tudo(client, user, client_profile, address):
    Contact.objects.create(full_name="Maria", subject="Oi", message="x", email=user.email, phone="75999999999")
    assert _delete(client, user).status_code == 200
    assert not User.objects.filter(pk=user.pk).exists()
    assert not AddressesClient.objects.filter(pk=address.pk).exists()
    assert not Contact.objects.filter(email=user.email).exists()


def test_exclusao_com_pedidos_anonimiza_e_preserva_o_pedido(client, user, client_profile, address, order, variant):
    OrderItem.objects.create(order_id=order, variant_id=variant, order_item_quantity=1, order_item_price="99.95")
    order.order_status = order.StatusOrder.COMPLETED  # só pedido concluído pode ser avaliado
    order.save()
    item = order.items.first()
    Reviews.objects.create(order_item_id=item, user_id=user, reviews=5, comment="Amei")
    outro = AddressesClient.objects.create(
        client_id=client_profile, cep="45200-000", street="Rua B", number="2",
        neighborhood="Centro", city="Jequié", state="BA", is_preferential=False,
    )
    Contact.objects.create(full_name="Maria", subject="Oi", message="x", email=user.email, phone="75999999999")
    email_original = user.email

    assert _delete(client, user).status_code == 200

    user.refresh_from_db()
    client_profile.refresh_from_db()
    assert user.email != email_original and user.email.endswith("@excluido.invalid")
    assert user.is_active is False
    assert user.has_usable_password() is False
    assert (client_profile.first_name, client_profile.last_name, client_profile.phone) == (None, None, None)
    assert client_profile.cpf is None and client_profile.cpf_hash is None
    # o pedido (dado fiscal) e o endereço de entrega dele continuam; o endereço sem pedido sai
    order.refresh_from_db()
    assert order.shipping_address_id == address.pk
    assert AddressesClient.objects.filter(pk=address.pk).exists()
    assert not AddressesClient.objects.filter(pk=outro.pk).exists()
    assert not Reviews.objects.filter(user_id=user).exists()
    assert not Contact.objects.filter(email=email_original).exists()


def test_exclusao_nunca_apaga_a_foto_padrao_compartilhada(client, user, client_profile, monkeypatch):
    apagadas = []
    monkeypatch.setattr("luxury_fashion.apps.accounts.repositories.client_repository.delete_old_media_file.delay",
                        lambda name: apagadas.append(name))
    assert client_profile.photo.name == DEFAULT_CLIENT_PHOTO
    _delete(client, user)
    assert apagadas == []


# ── export ───────────────────────────────────────────────────────────────

def test_export_traz_enderecos_pedidos_e_mensagens(client, user, client_profile, address, order, variant):
    OrderItem.objects.create(order_id=order, variant_id=variant, order_item_quantity=2, order_item_price="99.95")
    Contact.objects.create(full_name="Maria", subject="Dúvida", message="oi", email=user.email, phone="75999999999")
    client.patch("/api/auth/consents", data={"accepted_terms": True}, content_type="application/json", **auth_header(user))

    data = client.get("/api/auth/export-my-data", **auth_header(user)).json()

    assert data["conta"]["email"] == user.email
    assert data["consentimentos"]["versao_termos"] is not None
    assert data["perfil"]["cpf"] == "39053344705"
    assert data["enderecos"][0]["cidade"] == "Jequié"
    assert data["pedidos"][0]["codigo"] == order.code
    assert data["pedidos"][0]["itens"][0]["quantidade"] == 2
    assert data["mensagens_de_contato"][0]["assunto"] == "Dúvida"