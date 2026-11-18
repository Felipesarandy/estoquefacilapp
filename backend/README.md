# EstoqueFácil — backend (API REST)

API em Flask para o controle de estoque dos insumos de um haras: catálogo,
movimentações com baixa atômica, registro diário, alertas de quebra de
estoque (colchão mínimo e aviso com 5 dias de antecedência), inventário,
gestão de incidentes e trilha de auditoria (modelo ITIL).

Requisitos: Python 3.10 ou mais novo.

## 1. Instalação

Dentro de `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux/macOS
pip install -e ".[dev,test]"
```

## 2. Configuração (.env)

Copie o modelo comentado e ajuste as chaves:

```bash
copy .env.example .env            # Windows
cp .env.example .env              # Linux/macOS
```

| Variável | Para que serve | Padrão |
|---|---|---|
| `SECRET_KEY` | chave do Flask (obrigatória em produção) | valor inseguro de desenvolvimento |
| `JWT_SECRET_KEY` | assina os tokens (obrigatória em produção) | `SECRET_KEY` |
| `JWT_EXPIRES_SECONDS` | validade do token | `3600` |
| `DATABASE_URL` | banco de dados | `sqlite:///dev.db` (em `instance/`) |
| `CORS_ORIGINS` | origens do front-end | `http://localhost:5173,http://127.0.0.1:5173` |
| `TIMEZONE` | fuso do "hoje" e das previsões | `America/Sao_Paulo` |
| `ALERTA_DIAS_ANTECEDENCIA` | dias de antecedência do alerta `atencao` | `5` |
| `LOG_LEVEL` | nível dos logs | `INFO` |

O `.env` nunca vai para o Git. O Flask também encontra um `.env` na raiz
do repositório.

## 3. Banco de dados e dados de exemplo

```bash
flask db upgrade          # cria/atualiza as tabelas (migrations versionadas)
flask seed                # APAGA os dados e cria o haras de exemplo (pede confirmação)
flask seed --force        # o mesmo, sem perguntar
```

O banco SQLite fica em `instance/dev.db`. Para recriar do zero: apague
esse arquivo e rode `flask db upgrade` e `flask seed --force`.

Usuários do seed:

| E-mail | Senha | Papel |
|---|---|---|
| `admin@haras.com` | `admin123` | admin |
| `tratador@haras.com` | `trat123` | tratador |

O seed cria 7 insumos (um em ruptura, dois críticos, um em atenção e três
ok), movimentações dos últimos 7 dias, uma contagem de inventário com
divergência, incidentes (ruptura automática, divergência e um manual em
análise) e a trilha de auditoria.

## 4. Executar

```bash
flask run                 # http://localhost:5000/api/health
```

## 5. Testes

```bash
pytest                    # 302 testes, banco em memória
pytest -v tests/api       # só os testes de API
```

## Atalhos (invoke)

| Comando | Faz |
|---|---|
| `invoke install` | instala dependências de desenvolvimento e teste |
| `invoke upgrade` | aplica as migrations |
| `invoke seed` | recria o haras de exemplo (`flask seed --force`) |
| `invoke run` | sobe a API (`--port` opcional) |
| `invoke test` | roda os testes |
| `invoke migrate --msg "texto"` | gera migration nova (só uma pessoa do grupo) |

## Estrutura

```
backend/
  app/
    __init__.py      create_app (Application Factory), logging
    extensions.py    db, migrate, jwt
    seed.py          comando flask seed
    models/          uma entidade por arquivo + constants.py
    api/             um blueprint por recurso (prefixo /api), errors, security
    schemas/         validação e serialização (helpers em common.py)
    services/        regras: stock, alerts, catalog, inventory, incidents, audit
  migrations/        Alembic (d2b9e292d1e5 -> 84631ed584e8)
  tests/             models/, services/, api/, conftest.py
  docs/              documentação (abaixo)
  config.py          configuração por ambiente
  tasks.py           atalhos invoke
  .env.example       modelo comentado das variáveis
```

## Documentação

| Arquivo | Conteúdo |
|---|---|
| [docs/API.md](docs/API.md) | todos os endpoints, autenticação, erros, paginação |
| [docs/ER.md](docs/ER.md) | diagrama do banco (Mermaid) e entidades |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | camadas, segurança, logging, testes, critérios de avaliação |
| [docs/AUDITORIA_ITIL.md](docs/AUDITORIA_ITIL.md) | mapeamento ITIL, severidade, ciclo de vida, suposições |
| [docs/TRECHOS_PARA_PDF.md](docs/TRECHOS_PARA_PDF.md) | trechos de código comentados para o relatório |
| [docs/DESAFIOS.md](docs/DESAFIOS.md) | desafios técnicos e soluções |
