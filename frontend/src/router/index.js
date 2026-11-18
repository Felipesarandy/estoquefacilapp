import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'

// Rotas autenticadas: renderizadas dentro do AppLayout.
const appChildren = [
  { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { requiresAuth: true, title: 'Painel' } },
  { path: 'produtos', name: 'produtos', component: () => import('../views/ProductsView.vue'), meta: { requiresAuth: true, title: 'Produtos' } },
  { path: 'categorias', name: 'categorias', component: () => import('../views/CategoriesView.vue'), meta: { requiresAuth: true, title: 'Categorias' } },
  { path: 'fornecedores', name: 'fornecedores', component: () => import('../views/SuppliersView.vue'), meta: { requiresAuth: true, title: 'Fornecedores' } },
  { path: 'alertas', name: 'alertas', component: () => import('../views/AlertsView.vue'), meta: { requiresAuth: true, title: 'Alertas' } },
  { path: 'movimentacoes', name: 'movimentacoes', component: () => import('../views/MovementsView.vue'), meta: { requiresAuth: true, title: 'Movimentações' } },
  { path: 'registro-diario', name: 'registro-diario', component: () => import('../views/DailyLogView.vue'), meta: { requiresAuth: true, title: 'Registro diário' } },
  { path: 'inventario', name: 'inventario', component: () => import('../views/InventoryView.vue'), meta: { requiresAuth: true, title: 'Inventário' } },
  { path: 'incidentes', name: 'incidentes', component: () => import('../views/IncidentsView.vue'), meta: { requiresAuth: true, title: 'Incidentes' } },
  { path: 'auditoria', name: 'auditoria', component: () => import('../views/AuditView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: 'Auditoria' } },
  { path: 'usuarios', name: 'usuarios', component: () => import('../views/UsersView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: 'Usuários' } },
]

// Página de demonstração dos componentes: só existe em desenvolvimento.
if (import.meta.env.DEV) {
  appChildren.push({
    path: '_ui',
    name: 'ui-demo',
    component: () => import('../views/UiDemoView.vue'),
    meta: { requiresAuth: true, title: 'Componentes de interface' },
  })
}

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Entrar' },
  },
  { path: '/', component: AppLayout, children: appChildren },
  {
    path: '/:pathMatch(.*)*',
    name: 'nao-encontrado',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: 'Página não encontrada' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.name === 'login') {
    return auth.isAuthenticated ? { name: 'dashboard' } : true
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    useToastStore().warning('Você não tem permissão para acessar essa página.')
    return { name: 'dashboard' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · EstoqueFácil` : 'EstoqueFácil'
})

export default router
