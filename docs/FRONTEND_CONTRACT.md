<!-- luxury_fashion/docs/FRONTEND_CONTRACT.md -->
# Contrato back ↔ front — Gama Fashion

Tudo abaixo já está implementado no back; este documento só descreve como o front deve consumir.

## 1. Base
- API: `/api/...` (JSON). Health (infra, não é do front): `/health/live` e `/health/ready`.
- Todas as chamadas autenticadas levam `Authorization: Bearer <access>`.
- O front precisa estar em `CORS_ALLOWED_ORIGINS` (e `CSRF_TRUSTED_ORIGINS`) do back, e as chamadas de auth usam `credentials: 'include'`.

## 2. Autenticação (já implementada)
| Item | Como é |
|---|---|
| `access` (JWT curto, 15 min em prod) | vem no corpo (`{"access": "..."}`) de `/auth/login`, `/auth/register`, `/auth/google`, `/auth/refresh`. **Guardar só em memória** (nunca localStorage). |
| `refresh` | cookie **httpOnly** `eluxo_refresh_token` (nome legado), `path=/api/auth`. O JS não lê; o browser manda sozinho. |
| Renovar | `POST /api/auth/refresh` **sem body**, com `credentials: 'include'` → `{"access": "..."}` e o cookie é rotacionado. |
| Sair | `POST /api/auth/logout` (este aparelho) / `POST /api/auth/logout-all` (todos), com `credentials: 'include'`. |
| Sessões | `GET /api/auth/sessions`, `DELETE /api/auth/sessions/{session_id}`. |

Interceptor recomendado:
1. Requisição autenticada devolveu **401** → chamar `/auth/refresh` **uma vez**. Se já houver um refresh em andamento, aguardar a **mesma** promise (single-flight), senão várias abas/requests disparam refresh ao mesmo tempo e o segundo usa um refresh já rotacionado.
2. Refresh ok → repetir a requisição original com o novo `access`.
3. Refresh falhou (401/403) → limpar o estado local e ir para o login.

O back recusa `/refresh` e `/logout` quando o header `Origin` do browser não é uma origem confiável (defesa CSRF).

## 3. Erros — formato único
`detail` é **sempre texto**. Só o 422 traz também `errors`.

| Status | Corpo | Quando |
|---|---|---|
| 400 / 404 / 409 | `{"detail": "..."}` | regra de negócio / não encontrado / conflito |
| 401 | `{"detail": "..."}` | sem token, token inválido ou expirado |
| 403 | `{"detail": "..."}` | sem permissão (ou origem não autorizada no refresh) |
| 422 | `{"detail": "Dados inválidos.", "errors": [{"field", "message", "type"}]}` | validação |
| 429 | `{"detail": "..."}` | rate limit |
| 500 | `{"detail": "Erro interno do servidor."}` | erro não tratado |

- `errors[].field` é o caminho do campo no payload (`email`, `address.cep`, `items.0.quantity`) — use para marcar o campo no formulário. `field: ""` = erro geral do formulário. Em query/path é o nome do parâmetro.
- `errors[].message` vem em inglês (Pydantic). Traduza no front **pelo `type`** (`missing` → "Campo obrigatório", `string_too_short`, `int_parsing`...).
- Os valores enviados nunca voltam na resposta.

## 4. Convenções de dados
- Paginação: `?page=1&page_size=20` (máx. 100, acima disso o back limita) → `{items, total, page, page_size, pages}`.
- **Valores monetários (`Decimal`) chegam como string** (`"199.90"`). Converta com uma lib decimal; não faça conta com `float`.
- IDs são UUID (string); datas em ISO 8601.
- Envio do pedido (`shipping_status`): `pending → label_generated → shipped → in_transit → delivered`; use `shipping_status_label` para o texto e `shipping_tracking_code` para o rastreio.

## 5. Gerar o cliente TypeScript
```bash
# no back (gera o OpenAPI com os erros declarados e sem os webhooks)
docker compose -f docker-compose.dev.yml exec web python manage.py export_openapi --output openapi.json

# no front (uma das duas)
npx openapi-typescript ./openapi.json -o src/api/schema.d.ts
npx orval --input ./openapi.json --output ./src/api
```
- Os `operationId` são curtos (`auth_login`, `orders_list_orders_admin`) e viram `authLogin`, `ordersListOrdersAdmin`.
- Regenere o cliente sempre que o back mudar uma rota ou schema.
- Em produção `/api/docs` e `/api/openapi.json` ficam desligados (`API_DOCS_ENABLED=False`); o `export_openapi` funciona igual.

## 6. Sino de notificações
- Badge: `GET /api/notifications/unread-count` a cada 30–60 s (pausar com a aba oculta; refazer ao focar a janela).
- Lista: `GET /api/notifications?page=1&page_size=10` (`unread_only=true` opcional).
- Clique: `POST /api/notifications/{id}/read` e navegar para `action_url` (caminho relativo).
- `POST /api/notifications/read-all` e `DELETE /api/notifications/{id}`.

## 7. Admin de pedidos
`GET /api/orders/admin/list` (filtros `order_status`, `shipping_status`, `search`, `date_from`, `date_to`), `GET /api/orders/admin/summary`, `GET /api/orders/admin/{order_id}`, `POST /api/orders/{order_id}/mark-delivered` (409 se não pago ou sem etiqueta).

## 8. Vitrine, avaliações e carrinho
- `GET /api/products/`: filtros `search`, `product_category_id`, `gender`, `size`, `color`, `in_stock_only`, `min_price`, `max_price`. Tamanho, cor, estoque e preço valem para a **mesma variante**. `sort` ∈ `recent | name | price_asc | price_desc | rating`.
- `ProductListOut`/`ProductOut` trazem `average_rating` (string decimal, `"0.0"` = sem avaliações) e `total_reviews` — só avaliações autorizadas. Não precisa chamar `/reviews/products/{id}/summary` por card.
- `GET /api/reviews/products/{product_id}` é **paginado** (`PageOut`) e público; cada item tem `author_name` (ex.: `Maria S.`), nota, comentário, `size`, `color`. Não existe e-mail nem ID de usuário nessa resposta.
- Só é possível avaliar item de pedido **entregue** (`shipping_status = delivered`); antes disso a API responde 409.
- O carrinho (`CartOut`) só tem `total_price`. Frete **não** mora no carrinho: cotar em `POST /api/cart/shipping/quote` e enviar `shipping_service_code` no checkout.

## 9. Pedidos, endereços e estoque
- `GET /api/orders/` é **paginado**. `order_status = completed` significa **pago** (rótulo sugerido: "Pago"); o andamento da entrega vem de `shipping_status`.
- `OrderItemOut` tem `product_name`, `size`, `color` congelados na compra (use esses, não os de `variant`, para exibir histórico).
- Endereço já usado em pedido nunca é alterado: `PATCH /api/address/my-addresses/{id}` devolve um endereço **novo (outro `address_id`)** e o antigo some da lista. `DELETE` do mesmo tipo de endereço responde 204 e apenas o esconde. Sempre use o `address_id` da resposta.
- Excluir produto/variante já vendidos → **409** (desative em vez de excluir).
- Estorno de pedido pago ainda sem etiqueta devolve o estoque; depois de etiquetado/enviado a reposição é manual (ajuste de estoque).- Itens de carrinho e de pedido (`CartItemOut.variant`, `OrderItemOut.variant`) são `VariantWithProductOut`: além dos campos da variante trazem `product_id` (link `/produtos/{id}`), `product_name` e `cover_image_url` (capa; `null` se o produto não tem imagem). Para histórico de pedido, prefira `OrderItemOut.product_name/size/color` (congelados na compra).