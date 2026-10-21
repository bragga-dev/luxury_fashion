# Luxury Fashion — Backend

API de e-commerce de moda: catálogo, carrinho, pedidos, pagamento, frete com geração de etiqueta, avaliações, notificações e chat entre cliente e loja.

**Stack:** Python 3.12 · Django 6 · Django Ninja · PostgreSQL · Redis · Celery · Django Channels · MinIO (S3) · Docker

**Integrações:** Asaas (pagamentos) · Frenet (cotação de frete e etiquetas OneClick) · Google OAuth · Sentry (opcional)

---

## Sumário

1. [Arquitetura](#arquitetura)
2. [Rodando em desenvolvimento](#rodando-em-desenvolvimento)
3. [Variáveis de ambiente](#variáveis-de-ambiente)
4. [Testes](#testes)
5. [Endpoints](#endpoints)
6. [Integrações](#integrações)
7. [Tarefas agendadas](#tarefas-agendadas)
8. [Armazenamento (MinIO)](#armazenamento-minio)
9. [Produção](#produção)
10. [Comandos úteis](#comandos-úteis)
11. [Pendências conhecidas](#pendências-conhecidas)

---

## Arquitetura

```
luxury_fashion/
├── config/                 # settings (base/dev/prod/test), api.py (roteamento), celery, asgi/wsgi, storages
└── apps/
    ├── accounts/           # usuários, clientes, admins, endereços, auth (JWT + refresh em cookie), sessões
    ├── products/           # categorias, produtos, variantes, imagens, frete do produto, cotação Frenet
    ├── cart/               # carrinho e itens
    ├── payments/           # pedidos, pagamento Asaas, etiqueta Frenet, webhooks, e-mails de pedido
    ├── reviews/            # avaliações
    ├── notifications/      # notificações internas
    ├── chat/               # conversas, mensagens, anexos, WebSocket
    ├── website/            # campanhas e formulário de contato
    └── core/               # exceções, permissões, validadores, tokens, health, utilidades
```

Cada app segue a mesma separação em camadas:

| Camada | Responsabilidade |
|---|---|
| `api/` | Endpoints (Django Ninja). Só recebe, valida permissão e traduz exceções em status HTTP. |
| `schemas/` | Entrada e saída (Pydantic). |
| `services/` | Regras de negócio. |
| `selectors/` | Consultas de leitura. |
| `repositories/` | Escrita e acesso ao banco. |
| `integrations/` | Clientes HTTP de serviços externos (Asaas, Frenet). Sem regra de negócio. |
| `tasks/` | Tarefas Celery. |

As exceções de domínio ficam em `core/exceptions/` e são exportadas por `luxury_fashion.apps.core.exceptions`.

O contrato com o frontend (autenticação, formato de erros, paginação, geração do cliente TypeScript) está em [`docs/FRONTEND_CONTRACT.md`](docs/FRONTEND_CONTRACT.md).

---

## Rodando em desenvolvimento

Pré-requisitos: Docker e Docker Compose.

```bash
# 1. variáveis de ambiente
cp .env.example .env
# edite o .env (veja a seção "Variáveis de ambiente")

# 2. subir os serviços
docker compose -f docker-compose.dev.yml up --build

# 3. migrações e admin
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Serviços do `docker-compose.dev.yml`:

| Serviço | Função | Porta |
|---|---|---|
| `web` | API Django (`runserver`) | 8000 |
| `db` | PostgreSQL 16 | 5432 |
| `redis` | Cache, broker do Celery e channel layer | 6379 |
| `celery` | Worker | — |
| `beat` | Agendador do Celery | — |
| `minio` | Armazenamento S3 | 9000 (API) · 9001 (console) |

Após subir: API em `http://localhost:8000/api/`, documentação interativa em `/api/docs` (ligada só com `DEBUG`) e console do MinIO em `http://localhost:9001`.

Health checks: `GET /health/live` e `GET /health/ready`.

> O comando `createsuperuser` é customizado: cria o usuário ADMIN e o perfil de administrador juntos. Aceita `--email`, `--full_name` e `--noinput` (com a senha em `DJANGO_SUPERUSER_PASSWORD`).

---

## Variáveis de ambiente

O arquivo [`.env.example`](.env.example) lista todas. Resumo por grupo:

| Grupo | Variáveis principais |
|---|---|
| Django | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `FRONTEND_URL`, `BACKEND_URL`, `ADMIN_URL`, `API_DOCS_ENABLED` |
| Banco | `POSTGRES_*`, `DATABASE_URL` |
| Redis/Celery | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| MinIO/S3 | `MINIO_*`, `AWS_*` (use o usuário IAM da aplicação, nunca o root) |
| Criptografia | `FIELD_ENCRYPTION_KEY`, `CPF_ENCRYPTION_KEY`, `CPF_HASH_KEY` |
| E-mail | `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `ADMIN_EMAIL`, `STORE_NAME`, `CONTACT_NOTIFICATION_EMAIL` |
| Asaas | `ASAAS_API_KEY`, `ASAAS_BASE_URL`, `ASAAS_CUSTOMER_ID`, `ASAAS_WEBHOOK_TOKEN`, `ASAAS_PAYMENT_DUE_DAYS` |
| Frenet | `FRENET_API_KEY`, `FRENET_PARTNER_TOKEN`, `FRENET_WEBHOOK_BASE_URL`, `FRENET_WEBHOOK_TOKEN_VALUE` e demais |
| Google / cookies | `GOOGLE_CLIENT_ID`, `CSRF_TRUSTED_ORIGINS`, `COOKIE_SAMESITE`, `COOKIE_SECURE` |
| Pedidos | `ORDER_PENDING_EXPIRATION_HOURS` |
| Sentry | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` |

Nunca commite o `.env`. Gere segredos longos e aleatórios:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Testes

Os testes usam `luxury_fashion.config.settings.test` (definido no `pytest.ini`), com channel layer em memória. A integração com Asaas e Frenet é mockada.

```bash
# suíte completa
pytest luxury_fashion/apps

# com cobertura
pytest luxury_fashion/apps --cov

# só um app
pytest luxury_fashion/apps/payments/tests --cov=luxury_fashion/apps/payments --cov-report=term-missing
```

Dentro do container: `docker compose -f docker-compose.dev.yml exec web pytest luxury_fashion/apps --cov`.

---

## Endpoints

Todos sob `/api/`. Rotas autenticadas usam `Authorization: Bearer <access>`.

| Prefixo | Conteúdo |
|---|---|
| `/auth/` | Cadastro, login, Google, refresh, logout, sessões, verificação de e-mail, recuperação de senha |
| `/admin/` | Operações administrativas de conta |
| `/address/` | Endereços do cliente |
| `/categories/`, `/products/` | Catálogo, variantes, imagens |
| `/shipping/` | Cotação de frete |
| `/cart/` | Carrinho |
| `/orders/` | Pedidos do cliente e gestão administrativa, geração de etiqueta |
| `/payments` | Webhook do Asaas |
| `/shipping/webhooks/frenet/` | Webhooks de status e tracking da Frenet |
| `/reviews/` | Avaliações |
| `/notifications/` | Notificações |
| `/chat/conversations...` | Conversas, histórico, envio de mensagem com anexo, marcar como lida |
| `/campaigns/`, `/contact/` | Campanhas do site e formulário de contato |

Autenticação: o `access` (JWT curto) vem no corpo da resposta e deve ficar só em memória; o `refresh` é cookie `httpOnly` rotacionado em `POST /api/auth/refresh`. Detalhes e formato de erros estão no contrato do frontend.

### Chat

- REST: `/api/chat/conversations` (abrir/retomar), `/mine`, `/admin` (inbox, com filtro `status`), `/{id}`, `/{id}/messages` (GET histórico, POST multipart com até 5 anexos) e `/{id}/read`.
- WebSocket: `ws/chat/<conversation_id>/`, autenticado por JWT (`JWTAuthMiddleware`). Eventos `message` e `read`.
- Anexos ficam no bucket privado do MinIO e são servidos por URL assinada.

---

## Integrações

### Asaas (pagamentos)

- `ASAAS_BASE_URL` aponta para o **sandbox** por padrão (`https://api-sandbox.asaas.com/v3`). Em produção use `https://api.asaas.com/v3`.
- O webhook (`/api/payments...`) valida o token configurado no painel do Asaas contra `ASAAS_WEBHOOK_TOKEN`.
- Pedidos `PENDING` sem pagamento por mais de `ORDER_PENDING_EXPIRATION_HOURS` são cancelados por tarefa agendada.

### Frenet (frete e etiquetas)

- **Cotação:** `FRENET_API_KEY` (token de cliente). Endpoint `POST /api/shipping/...`.
- **Etiqueta (OneClick):** `POST /api/orders/{order_id}/generate-label`, somente admin. Exige `FRENET_PARTNER_TOKEN`, pedido pago, serviço de frete escolhido, CPF e telefone do cliente e peso/dimensões nas variantes.
- **A Frenet não tem ambiente de homologação.** Toda chamada do OneClick usa a produção e **debita a carteira real**. Faça testes com pedido barato, seu próprio endereço e cancele a etiqueta antes da postagem (cancelamento é pelo painel da Frenet).
- É preciso ter saldo depositado na carteira e limite de etiquetas liberado. Cadastrar cartão não deposita saldo.
- Nome do destinatário e dados fiscais não podem ser editados depois de criado o pedido na Frenet.
- **Webhooks:** a URL de notificação vai no payload de cada pedido. Como a Frenet não envia header de autenticação, o segredo vai na própria URL (`?token=`). Configure `FRENET_WEBHOOK_BASE_URL` (URL pública do backend) e `FRENET_WEBHOOK_TOKEN_VALUE` **antes de gerar a primeira etiqueta**: pedidos criados sem isso nunca recebem notificação e a URL não pode ser atualizada depois. Trocar o segredo faz os pedidos antigos receberem 401.
- Status do envio: `pending → label_generated → shipped → in_transit → delivered`.

### Google OAuth

Login com Google em `/api/auth/google`, validado com `GOOGLE_CLIENT_ID`.

---

## Tarefas agendadas

Definidas em `config/celery.py` (executadas pelo serviço `beat`):

| Tarefa | Quando |
|---|---|
| `expire_pending_orders` | a cada 30 minutos |
| `cleanup_old_notifications` | diariamente às 03:30 |
| `send_review_requests` | diariamente às 12:00 |

Também há tarefas disparadas por evento: e-mails de verificação, redefinição de senha, pedido e contato.

---

## Armazenamento (MinIO)

Três buckets: mídia (público), estáticos e **privado** (anexos do chat, acessados por URL assinada). A política do usuário da aplicação está em `infra/minio/app-policy.json`.

Para o link assinado abrir no navegador, defina **`MINIO_EXTERNAL_URL`** com o endereço pelo qual o navegador alcança o MinIO:

- dev: `http://localhost:9000`
- produção: a URL pública do MinIO, com protocolo e sem barra final (ex.: `https://storage.seudominio.com`), atrás de proxy reverso com certificado.

Ela é diferente de `AWS_S3_ENDPOINT_URL` (`http://minio:9000`), que é o endereço interno do Docker usado pelo backend para enviar arquivos. O host entra na assinatura, então o link precisa ser gerado já com o host público. Sem `MINIO_EXTERNAL_URL`, os links saem com `minio:9000`, que não abre fora do Docker. As URLs assinadas expiram em 1 hora.

---

## Produção

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

O serviço `web` roda `migrate`, `collectstatic` e `gunicorn` (3 workers). Há também `celery` (concorrência 4), `beat`, `db`, `redis`, `minio` e `createbuckets`.

Checklist:

- `DEBUG=False`; `API_DOCS_ENABLED` desligado (padrão em produção).
- `ADMIN_URL` diferente de `admin/`.
- `ASAAS_BASE_URL` de produção e `ASAAS_API_KEY` de produção.
- `FRENET_PARTNER_TOKEN`, `FRENET_WEBHOOK_BASE_URL` e `FRENET_WEBHOOK_TOKEN_VALUE` preenchidos.
- `MINIO_EXTERNAL_URL` com a URL pública do MinIO.
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `COOKIE_SECURE=True`.
- Não deixe `.env`, `venv/` nem `celerybeat-schedule` no repositório.
- Faça um ciclo real (pedido, pagamento, etiqueta, webhook) com valor baixo antes de abrir ao público.

---

## Comandos úteis

```bash
# exportar o OpenAPI (para gerar o cliente TypeScript do frontend)
docker compose -f docker-compose.dev.yml exec web python manage.py export_openapi --output openapi.json

# migrações
docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate

# shell
docker compose -f docker-compose.dev.yml exec web python manage.py shell
```

---

## Pendências conhecidas

- **WebSocket do chat em execução real:** `config/asgi.py` expõe apenas `get_asgi_application()`, sem `ProtocolTypeRouter` apontando para `chat.routing.websocket_urlpatterns`, e a produção sobe com `gunicorn` (WSGI). Os testes passam porque montam a aplicação ASGI por conta própria. Enquanto isso não for ligado, o chat funciona por REST, mas não em tempo real.
- **Cobertura de testes** em torno de 71%. Pontos mais baixos: tarefas de notificações, `auth`, `address` e as APIs de produtos.
- **Etiqueta Frenet:** o pedido é consolidado em um único volume (peso somado, maior comprimento e largura, alturas empilhadas). Valide com um pedido de vários itens se as medidas batem com a caixa real.