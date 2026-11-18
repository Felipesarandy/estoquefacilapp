# EstoqueFácil Equihealth

Controle de estoque dos insumos de um haras que usa o alimentador automático **Equihealth**: ração, volumoso (feno), suplementos e vitaminas. Trabalho de Programação Web Avançada II (UVV).

- Entradas: `compra`, `doacao`, `ajuste` (com lote e validade opcionais)
- Saídas: `abastecimento_alimentador`, `trato_manual`, `avaria`, `vencimento`, `furto`, `ajuste`
- Alertas de quebra de estoque (`ruptura`, `critico`, `atencao`, `ok`), dias de cobertura e capital imobilizado
- Inventário (contagem física x sistema), gestão de incidentes e trilha de auditoria (ITIL)

## Estrutura do repositório

| Pasta | O que é | Documentação |
|---|---|---|
| `backend/` | API REST em Flask + SQLAlchemy + JWT (SQLite em desenvolvimento) | [backend/README.md](backend/README.md) e [backend/docs/](backend/docs/) |
| `frontend/` | Interface em Vue 3 (em desenvolvimento), consome a API em `http://localhost:5000/api` | — |

O que mudou e os avisos para o grupo ficam em [changes.txt](changes.txt).

## Rodando o backend

No terminal do VS Code (`Ctrl + '`), dentro de `backend/`:

### 1. Primeira vez

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,test]"
copy .env.example .env
```

Depois: `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha `backend\.venv`.

O `.env` nunca vai para o Git. Ele pode ficar em `backend/` ou na raiz do repositório (o `.env.example` é o mesmo nos dois lugares).

### 2. Banco e dados de exemplo

```bash
python -m flask db upgrade        # aplica as migrations versionadas
python -m flask seed --force      # APAGA os dados e cria o haras de exemplo
```

O banco SQLite fica em `backend/instance/dev.db` (abra com a extensão **SQLite Viewer**).

| E-mail | Senha | Papel |
|---|---|---|
| `admin@haras.com` | `admin123` | admin |
| `tratador@haras.com` | `trat123` | tratador |

### 3. API e testes

```bash
python -m flask run               # http://localhost:5000/api/health
python -m pytest                  # testes automatizados, banco em memória
```

Usar `python -m flask` e `python -m pytest` evita erro de caminho quando a pasta do projeto muda de lugar.

### 4. Quando alterar os models

Só uma pessoa do grupo gera migrations. Depois de mudar algo em `backend/app/models/`, gere uma nova (nunca edite uma já aplicada):

```bash
python -m flask db migrate -m "descreva a mudança"
python -m flask db upgrade
```

## Front-end

Em desenvolvimento (Vue 3).
