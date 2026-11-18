# EstoqueFácil — frontend

Interface em Vue 3 (Composition API, `<script setup>`), Vite, Tailwind CSS v4, Pinia, Vue Router, Axios e Chart.js.
O guia completo (como rodar backend e frontend juntos) está no [README da raiz](../README.md).

```bash
npm install
cp .env.example .env     # Windows: copy .env.example .env
npm run dev              # http://localhost:5173
npm run build            # build de produção em dist/
```

`VITE_API_URL` (em `.env`) aponta para a API; o padrão é `http://localhost:5000/api`.

## Estrutura de `src/`

| Pasta | Conteúdo |
|---|---|
| `api/` | Um módulo por recurso da API; `http.js` tem o Axios, o token JWT e a conversão de erros (`ApiError`) |
| `stores/` | Pinia: `auth` (sessão), `toast` (avisos) |
| `router/` | Rotas com carregamento sob demanda e guards (`requiresAuth`, `requiresAdmin`) |
| `layouts/` | `AuthLayout` (login) e `AppLayout` (menu lateral + topo) |
| `views/` | Uma tela por rota |
| `components/ui/` | Componentes genéricos (botão, campos, modal, tabela, paginação...) |
| `components/domain/` | Componentes do negócio (formulários, selo de nível, gráfico...) |
| `composables/` | `useApiForm`, `useAsyncBlock`, `useCrudList`, `usePagination` |
| `utils/` | Formatação pt-BR, rótulos e cores (`constants.js`), CSV, auditoria |

A rota `/_ui` (catálogo de componentes) só existe em desenvolvimento (`npm run dev`).
