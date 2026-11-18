# EstoqueFácil Equihealth

Controle de estoque dos produtos de um haras que usa o alimentador automático **Equihealth**: ração, volumoso (feno), suplementos e vitaminas. Trabalho de Programação Web Avançada II (UVV).

O sistema responde a três perguntas do dia a dia: **o que tenho em estoque, o que vai acabar e quem mexeu em quê**. Há dois perfis: `admin` (cadastros, usuários, auditoria) e `tratador` (consulta e lança movimentações).

## Funcionalidades por tela

| Tela | O que faz | Perfil |
|---|---|---|
| **Painel** | Indicadores por nível de estoque, incidentes abertos, gráfico de entradas x saídas (7 dias), produtos que precisam de atenção e últimas movimentações | todos |
| **Produtos** | Lista com busca e filtros (categoria, nível, situação), cadastro, edição e desativação/reativação. O saldo só muda por movimentação | ver: todos; editar: admin |
| **Categorias** | Cadastro e edição. Exclusão só do admin e só se a categoria não tiver produtos (ativos ou inativos) | ver: todos; editar/excluir: admin |
| **Fornecedores** | Cadastro e edição com telefone e e-mail | ver: todos; editar: admin |
| **Alertas** | Quebra de estoque por nível (ruptura, crítico, atenção) com cobertura em dias e reposição sugerida; atalho para registrar entrada | todos |
| **Movimentações** | Histórico com filtros e registro de entrada/saída (saída acima do saldo é recusada). Movimentações são imutáveis; correção = movimentação de ajuste | todos |
| **Registro diário** | Resumo de entradas e saídas por dia (7, 15, 30 dias ou período livre), detalhe por produto e exportação em CSV | todos |
| **Inventário** | Contagem física x saldo do sistema; divergência gera ajuste e incidente | todos |
| **Incidentes** | Ciclo aberto → em análise → resolvido → fechado (ruptura e divergência abrem sozinhos; também há abertura manual) | ver/abrir: todos; mudar status: admin |
| **Auditoria** | Trilha imutável (quem, quando, IP, antes e depois), sem senhas | admin |
| **Usuários** | Criação, edição, redefinição de senha e desativação. Usuários nunca são excluídos | admin |

## Tecnologias

- **Backend:** Python 3.10+, Flask, SQLAlchemy, Alembic (Flask-Migrate), JWT, SQLite em desenvolvimento, pytest.
- **Frontend:** Vue 3 (Composition API), Vite, Tailwind CSS v4, Pinia, Vue Router, Axios, Chart.js.

## Estrutura do repositório

```
estoquefacilapp/
├── backend/        API REST (app/, migrations/, tests/, docs/)
│   └── docs/       API.md, ARQUITETURA.md, AUDITORIA_ITIL.md, DESAFIOS.md, ER.md
├── frontend/       Interface Vue (src/api, stores, router, layouts, views, components, composables, utils)
├── changes.txt     Avisos de mudanças para o grupo
└── .env.example    Modelo de variáveis do backend
```

Mais detalhes: [backend/README.md](backend/README.md), [backend/docs/API.md](backend/docs/API.md) e [frontend/README.md](frontend/README.md).

## Como rodar (dois terminais)

Pré-requisitos: Python 3.10+ e Node.js 20.19+ (ou 22.12+).

### Terminal 1 — backend (http://localhost:5000)

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,test]"
copy .env.example .env
python -m flask db upgrade
python -m flask seed --force
python -m flask run
```

**Windows (Git Bash):**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev,test]"
cp .env.example .env
python -m flask db upgrade
python -m flask seed --force
python -m flask run
```

**Linux/macOS:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,test]"
cp .env.example .env
python -m flask db upgrade
python -m flask seed --force
python -m flask run
```

`flask seed --force` **apaga os dados** e recria o haras de demonstração. Teste a API em http://localhost:5000/api/health.

### Terminal 2 — frontend (http://localhost:5173)

```bash
cd frontend
npm install
cp .env.example .env        # Windows (PowerShell): copy .env.example .env
npm run dev
```

O `.env` do frontend só tem `VITE_API_URL=http://localhost:5000/api`. O CORS do backend já libera `http://localhost:5173`.

### Usuários de demonstração

| E-mail | Senha | Perfil |
|---|---|---|
| `admin@haras.com` | `admin123` | admin |
| `tratador@haras.com` | `trat123` | tratador |

## Testes

```bash
cd backend
python -m pytest            # banco em memória; 313 testes
cd ../frontend
npm run build               # confere que o frontend compila
```

## Decisões do grupo

| Tema | Decisão |
|---|---|
| **Quebra de estoque** | Colchão mínimo (`min_stock`) por produto. Níveis: `ruptura` (saldo ≤ 0), `critico` (saldo ≤ colchão), `atencao` (cobertura ≤ 5 dias, configurável em `ALERTA_DIAS_ANTECEDENCIA`) e `ok` |
| **Registro diário** | Resumo por dia de entradas e saídas (total, por produto e por usuário), no fuso do haras (`America/Sao_Paulo`) |
| **Auditoria (ITIL)** | Trilha imutável de login, cadastros, movimentações, inventário e incidentes; incidentes seguem o ciclo aberto → em análise → resolvido → fechado; inventário (ativos) com ajuste automático |
| **Imutabilidade** | Movimentações, contagens e auditoria não são editadas nem excluídas |
| **Exclusão** | Só categorias podem ser excluídas (e apenas sem produtos). Produtos e usuários são desativados |
| **Termo** | "Produto" na interface; a API e alguns textos técnicos antigos ainda dizem "insumo" |

O histórico de mudanças e os avisos para o grupo ficam em [changes.txt](changes.txt); os desafios técnicos em [backend/docs/DESAFIOS.md](backend/docs/DESAFIOS.md).

## Quando alterar os models

Só uma pessoa do grupo gera migrations. Depois de mudar algo em `backend/app/models/`:

```bash
python -m flask db migrate -m "descreva a mudança"
python -m flask db upgrade
```
