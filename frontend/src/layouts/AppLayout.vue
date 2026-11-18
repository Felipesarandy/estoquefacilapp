<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '../components/ui/BaseButton.vue'
import { ROLES } from '../utils/constants'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const NAV_ITEMS = [
  { name: 'dashboard', label: 'Painel', path: '/' },
  { name: 'produtos', label: 'Produtos', path: '/produtos' },
  { name: 'categorias', label: 'Categorias', path: '/categorias' },
  { name: 'fornecedores', label: 'Fornecedores', path: '/fornecedores' },
  { name: 'alertas', label: 'Alertas', path: '/alertas' },
  { name: 'movimentacoes', label: 'Movimentações', path: '/movimentacoes' },
  { name: 'registro-diario', label: 'Registro diário', path: '/registro-diario' },
  { name: 'inventario', label: 'Inventário', path: '/inventario' },
  { name: 'incidentes', label: 'Incidentes', path: '/incidentes' },
  { name: 'auditoria', label: 'Auditoria', path: '/auditoria', admin: true },
  { name: 'usuarios', label: 'Usuários', path: '/usuarios', admin: true },
]

const items = computed(() => NAV_ITEMS.filter((i) => !i.admin || auth.isAdmin))
const roleLabel = computed(() => ROLES[auth.user?.role]?.label ?? auth.user?.role)

function isActive(item) {
  return item.path === '/' ? route.path === '/' : route.path.startsWith(item.path)
}

// Gaveta no celular; fixo em telas grandes (lg).
const drawerOpen = ref(false)
const isDesktop = ref(true)
const menuButton = ref(null)
let mediaQuery = null

function syncViewport() {
  isDesktop.value = mediaQuery.matches
  if (isDesktop.value) drawerOpen.value = false
}
function onKeydown(e) {
  if (e.key === 'Escape' && drawerOpen.value) {
    drawerOpen.value = false
    menuButton.value?.focus()
  }
}

onMounted(() => {
  mediaQuery = window.matchMedia('(min-width: 1024px)')
  syncViewport()
  mediaQuery.addEventListener('change', syncViewport)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', syncViewport)
  window.removeEventListener('keydown', onKeydown)
})
watch(() => route.path, () => (drawerOpen.value = false))

function sair() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <!-- Fundo escuro da gaveta -->
    <div
      v-if="drawerOpen"
      class="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
      aria-hidden="true"
      @click="drawerOpen = false"
    />

    <aside
      id="menu-principal"
      class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-900 text-slate-200 transition-transform duration-200 lg:translate-x-0"
      :class="drawerOpen ? 'translate-x-0' : '-translate-x-full'"
      :inert="!isDesktop && !drawerOpen"
      aria-label="Menu lateral"
    >
      <div class="flex h-16 shrink-0 items-center px-5 text-xl font-bold text-emerald-400">EstoqueFácil</div>
      <nav class="flex-1 overflow-y-auto px-3 pb-4" aria-label="Navegação principal">
        <ul class="space-y-1">
          <li v-for="item in items" :key="item.name">
            <RouterLink
              :to="{ name: item.name }"
              class="block rounded-lg px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-emerald-400"
              :class="
                isActive(item)
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              "
              :aria-current="isActive(item) ? 'page' : undefined"
            >
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>
    </aside>

    <div class="lg:pl-64">
      <header class="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
        <button
          ref="menuButton"
          type="button"
          class="rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-emerald-600 lg:hidden"
          aria-label="Abrir menu"
          aria-controls="menu-principal"
          :aria-expanded="drawerOpen"
          @click="drawerOpen = true"
        >
          <svg class="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" stroke-linecap="round" />
          </svg>
        </button>

        <h1 class="min-w-0 flex-1 truncate text-lg font-semibold text-slate-800">{{ route.meta.title }}</h1>

        <div class="hidden text-right text-sm leading-tight sm:block">
          <p class="font-medium text-slate-800">{{ auth.user?.name }}</p>
          <p class="text-slate-500">{{ roleLabel }}</p>
        </div>
        <BaseButton variant="secondary" size="sm" @click="sair">Sair</BaseButton>
      </header>

      <main class="p-4 sm:p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
