# Arquitetura do backend

API REST em **Flask 3** com **SQLAlchemy 2** (ORM), **Flask-Migrate/Alembic**
(migrations), **Flask-JWT-Extended** (autenticação), **Flask-Cors** e
**pytest**. Banco SQLite em desenvolvimento (PostgreSQL suportado via
`DATABASE_URL`). Python ≥ 3.10.

## Camadas

```
requisição HTTP
   │
   ▼
app/api/        Blueprints (uma rota fina por endpoint): autenticação/papel,
   │            lê a requisição, chama schema + serviço, faz o commit,
   │            devolve JSON e o status HTTP.
   ▼
app/schemas/    Validação da entrada (ValidationError → 422) e serialização
   │            da saída (Decimal como texto, datas ISO, nunca senha).
   ▼
app/services/   Regras de negócio, sem HTTP: baixa atômica de estoque,
   │            níveis de alerta, inventário, incidentes, auditoria,
   │            consultas do catálogo. Não fazem commit.
   ▼
app/models/     Entidades do ORM (um arquivo por tabela) + constantes de
                domínio. Sem dependência das camadas de cima.
```

Regra de dependência: `api → schemas/services → models`. Nenhum model,
schema ou serviço importa `app.api`. Os erros de regra de negócio
(`Conflito`, `ConflitoDeEstoque`, `TransicaoInvalida`) ficam em
`app/services/exceptions.py`, para os serviços se usarem sem importação
circular; a API os converte em 409.

Os serviços não dão commit: quem chama (rota ou seed) fecha a transação.
Assim uma saída de estoque, sua auditoria e o incidente de ruptura são
gravados juntos ou desfeitos juntos.

## Estrutura de pastas

```
backend/
  app/
    __init__.py        create_app (Application Factory)
    extensions.py      db, migrate, jwt (sem app)
    seed.py            comando `flask seed` (dados de demonstração)
    models/            stable, user, category, supplier, product,
                       stock_movement, inventory_count, incident,
                       audit_log, constants
    api/               __init__ (blueprint /api), errors, security,
                       health, auth, users, categories, suppliers,
                       products, movements, inventory, incidents,
                       alerts, dashboard, audit, meta
    schemas/           common (helpers) + um módulo por recurso
    services/          stock, alerts, catalog, inventory, incidents,
                       audit, exceptions
  migrations/          Alembic (2 revisões)
  tests/               models/, services/, api/ + conftest.py
  docs/                esta documentação
  config.py            configuração por ambiente (lê o .env)
  tasks.py             atalhos invoke (install, upgrade, seed, run, test)
  pyproject.toml       dependências e configuração do pytest
  .env.example         modelo das variáveis de ambiente
```

## Application Factory

`create_app(config_name)` (em `app/__init__.py`):

1. escolhe a configuração (`development`, `testing`, `production`) por
   argumento ou `FLASK_CONFIG`;
2. configura o logging;
3. em produção, recusa subir com `SECRET_KEY` padrão ou sem `JWT_SECRET_KEY`;
4. liga as extensões (`db`, `migrate` com `render_as_batch=True` para o
   SQLite, `jwt`, CORS em `/api/*`);
5. registra os models, os blueprints (`register_blueprints`) e o comando
   `flask seed`.

As extensões nascem sem app em `app/extensions.py`, o que permite criar
várias instâncias (uma por teste, com banco em memória).

## Blueprints e rotas

Cada recurso tem um módulo em `app/api/` com seu `Blueprint`; todos são
pendurados no blueprint `api` (prefixo `/api`) em `app/api/__init__.py`.
São 37 rotas (lista completa em [API.md](API.md)).

## Segurança

- **JWT**: `POST /api/auth/login` devolve o token (identity = id do usuário,
  claims `role` e `stable_id`). Validade configurável.
- **Papéis**: `roles_required(*roles)` em `app/api/security.py` valida o
  token, recarrega o usuário (401 se inexistente/inativo) e confere o papel
  (403). Atalhos `admin_required` e `login_required`.
- **Isolamento por haras**: toda consulta filtra `stable_id` do usuário.
- **Senhas**: só o hash (Werkzeug); nunca serializado nem auditado.
- **Login**: mesma mensagem para e-mail inexistente, senha errada e usuário
  inativo; tentativas falhas são auditadas e logadas.
- **CORS** restrito às origens de `CORS_ORIGINS`.

## Tratamento de erros

`app/api/errors.py` registra handlers para `ValidationError` (422 ou 400),
`Conflito` (409, com rollback da sessão), qualquer `HTTPException` (404,
405...) e exceções inesperadas (500, com log do stack trace). Todas
respondem `{"error": {"status", "message", "details"?}}`. As falhas de JWT
também usam esse formato, com mensagens em português.

## Logging

Configurado em `create_app` (`_configurar_logging`): console, nível por
`LOG_LEVEL` (padrão INFO), formato `data | nível | módulo | mensagem`.
Eventos registrados: movimentação (`INFO`), saída recusada por estoque
insuficiente (`WARNING`), login falho (`WARNING`), incidente aberto e
mudança de status (`INFO`), erro não tratado (`ERROR` com traceback).

## Configuração

`config.py` lê variáveis de ambiente (o `.env` é carregado pelo
python-dotenv via Flask CLI). Modelo comentado em `.env.example`:
`SECRET_KEY`, `JWT_SECRET_KEY`, `JWT_EXPIRES_SECONDS`, `DATABASE_URL`,
`CORS_ORIGINS`, `TIMEZONE`, `ALERTA_DIAS_ANTECEDENCIA`, `LOG_LEVEL`.
`TestingConfig` usa SQLite em memória.

## Testes

306 testes com pytest + pytest-flask, todos com banco em memória criado e
destruído a cada teste (`tests/conftest.py`):

| Pasta | O que cobre |
|---|---|
| `tests/models/` | models, constraints, imutabilidade de auditoria e contagem |
| `tests/services/` | regras: estoque atômico, alertas, inventário, incidentes, auditoria |
| `tests/api/` | cada endpoint: sucesso, validação (422), permissões (401/403), isolamento entre haras (404), conflitos (409), 405, paginação, filtros, seed |

Fixtures principais: `app`, `client`, `haras`, `admin`, `tratador`,
`outro_haras`, `auth_headers`, `insumo` (fábrica de insumos com saldo,
mínimo e consumo controlados).

## Critérios de avaliação → onde estão no código

| # | Critério | Onde |
|---|---|---|
| 1 | Application Factory | `app/__init__.py` (`create_app`), `app/extensions.py`, `config.py` |
| 2 | Módulos, blueprints e rotas | `app/api/__init__.py` + um blueprint por recurso em `app/api/*.py` |
| 3 | Formulários e validação no servidor | `app/schemas/common.py` (helpers, `ValidationError`) e `app/schemas/*.py`; handler 422/400 em `app/api/errors.py` |
| 4 | Interface | front-end Vue 3 em `frontend/` (fora deste backend); a API expõe `/api/meta` para os formulários |
| 5 | Testes automatizados | `tests/` (306 testes, `pytest`) |
| 6 | ORM e modelagem | `app/models/*.py`, `migrations/versions/*.py`, [ER.md](ER.md) |
| 7 | Qualidade | camadas `api/schemas/services/models`; `.env.example` + `config.py`; logging em `create_app`; erros em `app/api/errors.py`; `tasks.py`; documentação em `docs/` |

## Por que esta stack

- **Flask**: pequeno, explícito e exigido pela disciplina; blueprints e a
  Application Factory organizam o projeto sem mágica.
- **SQLAlchemy 2 + Alembic**: ORM maduro, `Numeric` para quantidades e
  dinheiro (sem erro de `float`), migrations versionadas e portáveis entre
  SQLite e PostgreSQL.
- **JWT (Flask-JWT-Extended)**: autenticação sem estado, adequada a um
  front-end SPA (Vue) consumindo a API.
- **SQLite em desenvolvimento**: zero instalação para o grupo; o
  `UPDATE` condicional garante a baixa atômica também nele.
- **pytest**: fixtures simples e banco em memória por teste.
