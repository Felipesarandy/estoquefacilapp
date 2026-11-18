# API REST — EstoqueFácil (haras)

Base: `http://localhost:5000/api` · formato: JSON (UTF-8) · 36 rotas
(lista conferida com `flask routes`).

## Convenções

- **Recursos no plural** (`/api/products`), verbos `GET`, `POST`, `PATCH`.
  Não há `PUT`. `DELETE` não existe em nenhum recurso: cadastros são
  desativados (`PATCH {"active": false}`) e movimentações, contagens,
  incidentes e auditoria são imutáveis ou encerrados pelo ciclo de vida.
  Método não suportado → **405**.
- **Escopo por haras**: toda consulta é filtrada pelo `stable_id` do usuário
  do token. Um id de outro haras responde **404** (no caminho) ou **422**
  (quando vem no corpo, como `category_id` ou `assigned_to_id`).
- **Campos que espelham colunas** em inglês (`type`, `status`, `reason`,
  `quantity`...); **rótulos de resumo** em português (`entradas`, `saidas`,
  `por_nivel`...).
- **Números decimais** saem como texto (`"85.000"`) para não perder casas;
  datas em ISO 8601. Horários (`created_at`) são gravados em UTC; o "dia" do
  registro diário usa o fuso `TIMEZONE` (padrão `America/Sao_Paulo`).

### Códigos de status

| Código | Quando |
|---|---|
| 200 | Consulta ou atualização bem-sucedida |
| 201 | Recurso criado |
| 400 | Corpo ausente ou que não é um objeto JSON |
| 401 | Sem token, token inválido/expirado, usuário inativo, login inválido |
| 403 | Papel sem permissão (ex.: tratador em rota de admin) |
| 404 | Rota ou recurso inexistente (ou de outro haras) |
| 405 | Método não permitido no recurso |
| 409 | Conflito: duplicidade, estoque insuficiente, insumo inativo, transição de incidente inválida |
| 422 | Dados inválidos (o campo vem em `details.field`) |

### Formato de erro

Todo erro, de qualquer rota, sai neste formato:

```json
{"error": {"status": 422, "message": "reason deve ser um destes: compra, doacao, ajuste", "details": {"field": "reason"}}}
```

`details` só aparece quando há algo a detalhar.

### Paginação

Listagens aceitam `?page=` (padrão 1) e `?per_page=` (padrão 20, máximo
100; acima disso é limitado a 100) e respondem:

```json
{"items": [ ... ], "page": 1, "per_page": 20, "total": 42}
```

### Autenticação

JWT no cabeçalho `Authorization: Bearer <access_token>`, obtido em
`POST /api/auth/login`. Validade em `JWT_EXPIRES_SECONDS` (padrão 3600 s).

| Acesso | Quem |
|---|---|
| público | sem token |
| `login_required` | admin ou tratador |
| `admin_required` | só admin |

Falhas de token (401): `Token de acesso obrigatório`, `Token inválido`,
`Token expirado`, `Token revogado`.

---

## Saúde

| Método | Caminho | Acesso |
|---|---|---|
| GET | `/api/health` | público |

`200` → `{"status": "ok"}`

## Autenticação — `/api/auth`

| Método | Caminho | Acesso | Corpo | Status |
|---|---|---|---|---|
| POST | `/api/auth/login` | público | `email`, `password` | 200, 400, 401, 422 |
| GET | `/api/auth/me` | login_required | — | 200, 401 |

- O e-mail é comparado em minúsculas. E-mail inexistente, senha errada e
  usuário inativo recebem a **mesma** resposta 401 `Credenciais inválidas`.
- Login e falha de login são auditados (`login` / `login_failed`).
- Não existe cadastro público: o primeiro admin vem do `flask seed`.

Exemplo `200` do login:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {"id": 1, "name": "Felipe Admin", "email": "admin@haras.com", "role": "admin",
           "active": true, "stable_id": 1, "created_at": "2026-11-18T01:27:25"}
}
```

O token carrega `sub` (id do usuário) e as claims `role` e `stable_id`.

## Usuários — `/api/users` (admin_required)

| Método | Caminho | Parâmetros / corpo | Status |
|---|---|---|---|
| GET | `/api/users` | `page`, `per_page`, `?active=true\|false`, `?role=admin\|tratador` | 200, 422 |
| POST | `/api/users` | `name`, `email`, `password` (mín. 8), `role` (padrão `tratador`) | 201, 409 (e-mail), 422 |
| GET | `/api/users/<id>` | — | 200, 404 |
| PATCH | `/api/users/<id>` | `name`, `active`, `role`, `password` (só os enviados) | 200, 404, 409, 422 |

- Ordenado por nome. Nunca devolve `password_hash`.
- O admin não pode desativar a si mesmo nem mudar o próprio papel (409).
- Auditado: `create`, `update`, `deactivate` (a senha nunca vai para a
  trilha; uma troca aparece só como `"password_changed": true`).

## Categorias — `/api/categories` e Fornecedores — `/api/suppliers`

| Método | Caminho | Acesso | Parâmetros / corpo | Status |
|---|---|---|---|---|
| GET | `/api/categories` | login_required | `page`, `per_page`, `?search=` (nome) | 200 |
| POST | `/api/categories` | admin_required | `name` | 201, 409, 422 |
| GET | `/api/categories/<id>` | login_required | — | 200, 404 |
| PATCH | `/api/categories/<id>` | admin_required | `name` | 200, 404, 409, 422 |
| GET | `/api/suppliers` | login_required | `page`, `per_page`, `?search=` | 200 |
| POST | `/api/suppliers` | admin_required | `name`, `phone`, `email` | 201, 409, 422 |
| GET | `/api/suppliers/<id>` | login_required | — | 200, 404 |
| PATCH | `/api/suppliers/<id>` | admin_required | `name`, `phone`, `email` | 200, 404, 409, 422 |

Nome único dentro do haras (comparação sem diferenciar maiúsculas) → 409.
Exemplo de item: `{"id": 1, "name": "Ração", "stable_id": 1}`.

## Insumos — `/api/products`

| Método | Caminho | Acesso | Parâmetros / corpo | Status |
|---|---|---|---|---|
| GET | `/api/products` | login_required | `page`, `per_page`, `?search=` (nome ou código), `?category_id=`, `?active=` | 200, 422 |
| POST | `/api/products` | admin_required | `name`, `category_id`, `code`, `supplier_id`, `unit`, `cost_price`, `min_stock`, `max_stock`, `daily_consumption`, `active` | 201, 409, 422 |
| GET | `/api/products/<id>` | login_required | — | 200, 404 |
| PATCH | `/api/products/<id>` | admin_required | mesmos campos (só os enviados) | 200, 404, 409, 422 |

- `current_stock` **não** é editável (422): o saldo só muda por movimentação.
- `unit` ∈ `kg, g, sc, l, ml, un`; `max_stock` ≥ `min_stock`; categoria e
  fornecedor do mesmo haras (422); `code` único no haras (409).
- Baixa lógica: `PATCH {"active": false}` (auditado como `deactivate`).

Exemplo `GET /api/products/3`:

```json
{
  "id": 3, "name": "Ração extrusada performance", "code": "EQ002", "unit": "kg",
  "category_id": 1, "supplier_id": 1, "stable_id": 1, "active": true,
  "cost_price": "5.80", "min_stock": "50.000", "max_stock": null,
  "current_stock": "85.000", "daily_consumption": "8.000", "stock_value": "493.00000",
  "nivel": "ok", "cobertura_dias": "10.625", "data_prevista_ruptura": "2026-11-27",
  "min_stock_sugerido": "40.000", "days_left": "10.625", "is_low_stock": false
}
```

## Movimentações — `/api/movements` (login_required: admin e tratador)

| Método | Caminho | Parâmetros / corpo | Status |
|---|---|---|---|
| POST | `/api/movements` | `product_id`, `type` (`entrada`\|`saida`), `quantity` (> 0, até 3 casas), `reason`, `batch`, `expiration_date` (YYYY-MM-DD), `note` | 201, 404, 409, 422 |
| GET | `/api/movements` | `page`, `per_page`, `?product_id=`, `?type=`, `?reason=`, `?user_id=`, `?from=`, `?to=` (YYYY-MM-DD) | 200, 422 |
| GET | `/api/movements/<id>` | — | 200, 404 |
| GET | `/api/movements/daily` | `?date=YYYY-MM-DD` (padrão: hoje) **ou** `?from=&to=` (máx. 31 dias) | 200, 422 |

- `reason` depende do tipo — entrada: `compra, doacao, ajuste`; saída:
  `abastecimento_alimentador, trato_manual, avaria, vencimento, furto, ajuste`.
- Saída maior que o saldo → **409 `Estoque insuficiente`** (saldo intacto);
  insumo inativo → 409; insumo de outro haras → 404.
- Imutável: sem `PATCH`/`PUT`/`DELETE` (405). Estorno = nova movimentação
  com `reason: "ajuste"` e `note` explicando.
- Efeitos na mesma transação: auditoria `movement`; se o saldo zerar, abre
  incidente de **ruptura**; se voltar a ter saldo, o incidente é resolvido
  com `Reposição registrada`.
- Histórico em ordem do mais recente para o mais antigo.

Exemplo `201`:

```json
{
  "movement": {"id": 39, "product_id": 3, "user_id": 1, "type": "entrada", "reason": "compra",
               "quantity": "50.000", "unit_cost": "5.80", "total_cost": "290.00000",
               "batch": "L2701B", "expiration_date": "2027-06-30", "note": null,
               "created_at": "2026-11-18T01:27:43"},
  "current_stock": "135.000",
  "nivel": "ok",
  "is_low_stock": false
}
```

Exemplo `GET /api/movements/daily` (listas encurtadas):

```json
{
  "from": "2026-11-17", "to": "2026-11-17",
  "dias": [{
    "data": "2026-11-17", "entradas": "0", "saidas": "84.000", "saldo": "-84.000",
    "total_movimentacoes": 5,
    "produtos": [{"id": 5, "name": "Feno de tifton (fardo)", "entradas": "0",
                  "saidas": "8.000", "saldo": "-8.000", "total_movimentacoes": 2}],
    "usuarios": [{"id": 2, "name": "João Tratador", "entradas": "0",
                  "saidas": "83.000", "saldo": "-83.000", "total_movimentacoes": 4}]
  }]
}
```

## Alertas (quebra de estoque) — `/api/alerts` (login_required)

| Método | Caminho | Parâmetros | Status |
|---|---|---|---|
| GET | `/api/alerts` | `page`, `per_page`, `?nivel=ruptura\|critico\|atencao` | 200, 422 |

Insumos **ativos** fora de `ok`, do mais grave para o menos grave e, no
mesmo nível, da menor cobertura para a maior. Níveis: `ruptura` (saldo ≤ 0),
`critico` (saldo ≤ `min_stock`), `atencao` (cobertura ≤
`ALERTA_DIAS_ANTECEDENCIA`, padrão 5 dias).

```json
{
  "dias_antecedencia": 5, "page": 1, "per_page": 1, "total": 4,
  "items": [{"id": 2, "name": "Suplemento vitamínico em pó", "code": "EQ300", "unit": "kg",
             "category_id": 4, "supplier_id": 1, "current_stock": "0.000", "min_stock": "2.000",
             "daily_consumption": "0.200", "cobertura_dias": "0",
             "data_prevista_ruptura": "2026-11-17", "min_stock_sugerido": "1.000",
             "nivel": "ruptura"}]
}
```

## Painel — `/api/dashboard` (login_required)

| Método | Caminho | Status |
|---|---|---|
| GET | `/api/dashboard` | 200 |

Campos: `produtos_ativos`, `por_nivel` (ruptura/critico/atencao/ok),
`em_alerta`, `mais_urgentes` (10, formato de alerta), `movimentacoes_hoje`
(data, entradas, saidas, saldo, total_movimentacoes),
`ultimas_movimentacoes` (10), `dias_antecedencia` e `incidentes_abertos`
(incidentes `aberto` + `em_analise`).

## Inventário — `/api/inventory` (login_required)

| Método | Caminho | Parâmetros / corpo | Status |
|---|---|---|---|
| POST | `/api/inventory` | `product_id`, `counted_quantity` (≥ 0), `note` | 201, 404, 409, 422 |
| GET | `/api/inventory` | `page`, `per_page`, `?product_id=`, `?from=`, `?to=` | 200, 422 |
| GET | `/api/inventory/<id>` | — | 200, 404 |

A contagem guarda o saldo do sistema no momento. Havendo diferença, gera a
movimentação de **ajuste** (saída se faltou, entrada se sobrou; `note`
"Ajuste após inventário #id") e abre incidente `divergencia_inventario`
com severidade proporcional. Imutável (sem `PATCH`/`PUT`/`DELETE`).

```json
{
  "count": {"id": 2, "product_id": 6, "user_id": 1, "system_quantity": "12.000",
            "counted_quantity": "10.000", "difference": "-2.000", "created_at": "2026-11-18T01:27:25"},
  "difference": "-2.000",
  "adjustment": {"id": 39, "type": "saida", "reason": "ajuste", "quantity": "2.000",
                 "note": "Ajuste após inventário #2: Contagem mensal", "...": "..."},
  "incident": {"id": 2, "type": "divergencia_inventario", "status": "aberto", "severity": "media", "...": "..."},
  "current_stock": "10.000",
  "nivel": "critico"
}
```

## Incidentes — `/api/incidents`

| Método | Caminho | Acesso | Parâmetros / corpo | Status |
|---|---|---|---|---|
| GET | `/api/incidents` | login_required | `page`, `per_page`, `?status=`, `?type=`, `?product_id=`, `?assigned_to_id=` | 200, 422 |
| GET | `/api/incidents/summary` | login_required | — | 200 |
| GET | `/api/incidents/<id>` | login_required | — | 200, 404 |
| POST | `/api/incidents` | login_required | `type`, `description`, `severity` (opcional), `product_id` (opcional) | 201, 409, 422 |
| PATCH | `/api/incidents/<id>` | admin_required | `status`, `assigned_to_id` (`null` remove), `resolution` | 200, 403, 404, 409, 422 |

- Tipos: `ruptura, divergencia_inventario, avaria, vencimento, furto, outro`.
  Severidade: `baixa, media, alta, critica` (padrão `media`; ruptura sempre `critica`).
- Abrir um incidente igual a um ainda ativo (mesmo insumo e tipo, `aberto`
  ou `em_analise`) → 409 com `details.incident_id` do existente.
- Transições: `aberto → em_analise | resolvido`; `em_analise → resolvido |
  aberto`; `resolvido → fechado | em_analise`; `fechado` é final. Outra
  transição → 409 (`Transição inválida: resolvido -> aberto`). Resolver sem
  `resolution` → 422. `assigned_to_id` de outro haras → 422.
- Auditado como `incident` (abertura e cada alteração, com antes/depois).

Exemplo `GET /api/incidents/summary`:

```json
{"total": 3, "por_status": {"aberto": 2, "resolvido": 1},
 "por_tipo": {"avaria": 1, "divergencia_inventario": 1, "ruptura": 1},
 "encerrados": 1, "tempo_medio_resolucao_horas": 0.0}
```

## Auditoria — `/api/audit` (admin_required, somente leitura)

| Método | Caminho | Parâmetros | Status |
|---|---|---|---|
| GET | `/api/audit` | `page`, `per_page`, `?action=`, `?entity=`, `?entity_id=`, `?user_id=`, `?from=`, `?to=` | 200, 403, 422 |
| GET | `/api/audit/<id>` | — | 200, 403, 404 |

Mais recentes primeiro. `action` ∈ `login, login_failed, create, update,
deactivate, movement, inventory, incident`; `entity` ∈ `user, category,
supplier, product, movement, inventory_count, incident`. Escrita pela API →
405; alteração pelo ORM → erro (registro imutável).

```json
{
  "id": 63, "stable_id": 1, "user_id": 1, "action": "incident", "entity": "incident", "entity_id": 3,
  "before_json": {"status": "em_analise", "resolution": null, "...": "..."},
  "after_json": {"status": "resolvido", "resolution": "Sacos descartados e depósito ventilado", "...": "..."},
  "ip": "127.0.0.1", "created_at": "2026-11-18T01:27:25"
}
```

## Metadados — `/api/meta` (login_required)

`GET /api/meta` devolve as listas de domínio para montar formulários:
`motivos_entrada`, `motivos_saida`, `motivos_perda`, `unidades`, `roles`,
`niveis_estoque`, `incident_types`, `incident_status`, `incident_severity`,
`audit_actions`.
