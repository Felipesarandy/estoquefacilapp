<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { listAlerts } from '../api/alerts'
import { listCategories } from '../api/categories'
import { getDashboard } from '../api/dashboard'
import { listAllProducts } from '../api/products'
import StatCard from '../components/domain/StatCard.vue'
import StockLevelBadge from '../components/domain/StockLevelBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { STOCK_LEVELS } from '../utils/constants'
import { formatDecimal, formatQuantity, formatTime } from '../utils/format'

const PER_PAGE = 10
const LEVELS = Object.keys(STOCK_LEVELS) // ruptura, critico, atencao, ok
const GRAVITY = Object.fromEntries(LEVELS.map((l, i) => [l, i]))

const route = useRoute()
const router = useRouter()

// ---- Estado na URL: ?nivel=&ok=1&page= ----------------------------------------
const nivel = computed(() => (LEVELS.includes(route.query.nivel) ? route.query.nivel : ''))
const showOk = computed(() => route.query.ok === '1' || nivel.value === 'ok')
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))

function queryWith(patch, { keepPage = false } = {}) {
  const next = { ...route.query, ...patch }
  if (!keepPage) delete next.page
  for (const key of Object.keys(next)) {
    if (next[key] === '' || next[key] === null || next[key] === undefined || next[key] === false) delete next[key]
  }
  if (next.page === 1) delete next.page
  return next
}
const setQuery = (patch, opts) => router.push({ query: queryWith(patch, opts) })

function toggleShowOk(checked) {
  // Desmarcar enquanto o filtro é "ok" também limpa o filtro.
  setQuery({ ok: checked ? '1' : '', nivel: !checked && nivel.value === 'ok' ? '' : nivel.value })
}
const cardTarget = (level) => ({ name: 'alertas', query: queryWith({ nivel: nivel.value === level ? '' : level }) })

// ---- Dados de apoio (resumo, categorias e produtos para reposição) ----------------
const summary = useAsyncBlock(getDashboard)
const categories = useAsyncBlock(() => listCategories({ per_page: 100 }))
const products = useAsyncBlock(() => listAllProducts({ active: true }))

const days = computed(() => summary.data.value?.dias_antecedencia ?? null)
const categoryNames = computed(() => new Map((categories.data.value?.items ?? []).map((c) => [c.id, c.name])))
const productsById = computed(() => new Map((products.data.value ?? []).map((p) => [p.id, p])))

// ---- Lista --------------------------------------------------------------------
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const updatedAt = ref(null)
let requestId = 0

const byGravity = (a, b) => {
  const cov = (x) => (x.cobertura_dias === null || x.cobertura_dias === undefined ? Infinity : Number(x.cobertura_dias))
  return GRAVITY[a.nivel] - GRAVITY[b.nivel] || cov(a) - cov(b) || a.name.localeCompare(b.name, 'pt-BR')
}

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    let result
    if (showOk.value) {
      // /alerts não devolve "ok": usa a lista de produtos ativos e ordena como o backend.
      const all = await listAllProducts({ active: true })
      if (id !== requestId) return
      products.data.value = all
      const filtered = all.filter((p) => !nivel.value || p.nivel === nivel.value).sort(byGravity)
      const start = (page.value - 1) * PER_PAGE
      result = { items: filtered.slice(start, start + PER_PAGE), total: filtered.length }
    } else {
      result = await listAlerts({ nivel: nivel.value || undefined, page: page.value, per_page: PER_PAGE })
    }
    if (id !== requestId) return
    rows.value = result.items
    total.value = result.total
    updatedAt.value = new Date()
    if (!result.items.length && result.total > 0 && page.value > 1) {
      router.replace({ query: queryWith({ page: Math.ceil(result.total / PER_PAGE) }, { keepPage: true }) })
    }
  } catch (err) {
    if (id !== requestId) return
    error.value = err.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

function refreshAll() {
  summary.load()
  load()
  if (!showOk.value) products.load() // com "ok" a lista de produtos já é recarregada por load()
}

watch(
  () => route.query,
  () => {
    if (route.name === 'alertas') load()
  },
)
onMounted(() => {
  summary.load()
  categories.load()
  products.load()
  load()
})

// ---- Tabela -------------------------------------------------------------------
const columns = [
  { key: 'name', label: 'Produto' },
  { key: 'nivel', label: 'Nível' },
  { key: 'current_stock', label: 'Estoque atual' },
  { key: 'min_stock', label: 'Colchão mínimo' },
  { key: 'daily_consumption', label: 'Consumo diário' },
  { key: 'cobertura_dias', label: 'Cobertura' },
  { key: 'reposicao', label: 'Reposição sugerida' },
  { key: 'actions', label: 'Ações' },
]
const coverage = (row) =>
  row.cobertura_dias === null || row.cobertura_dias === undefined ? '—' : `${formatDecimal(row.cobertura_dias)} dia(s)`

function restock(row) {
  const max = productsById.value.get(row.id)?.max_stock
  if (max === null || max === undefined) return '—'
  const diff = Number(max) - Number(row.current_stock)
  return diff > 0 ? formatQuantity(diff.toFixed(3), row.unit) : '—'
}
const categoryOf = (row) => categoryNames.value.get(row.category_id) ?? ''

const linkClass =
  'text-sm font-medium text-emerald-700 hover:underline focus-visible:outline-2 focus-visible:outline-emerald-600'
</script>

<template>
  <div class="space-y-5">
    <p class="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
      Colchão mínimo é o estoque de segurança definido por produto. Alertamos quando o estoque chega ao colchão ou a
      cobertura prevista fica em até {{ days ?? 'alguns' }} dias.
    </p>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <label class="inline-flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          class="size-4 rounded border-slate-300 text-emerald-600 focus-visible:outline-2 focus-visible:outline-emerald-600"
          :checked="showOk"
          @change="toggleShowOk($event.target.checked)"
        />
        Mostrar também OK
      </label>
      <div class="flex items-center gap-3">
        <span v-if="updatedAt" class="text-sm text-slate-500">Atualizado às {{ formatTime(updatedAt) }}</span>
        <BaseButton variant="secondary" size="sm" :loading="loading || summary.loading.value" @click="refreshAll">
          Atualizar
        </BaseButton>
      </div>
    </div>

    <!-- Cartões por nível: clicar filtra a lista -->
    <section aria-labelledby="titulo-niveis">
      <h2 id="titulo-niveis" class="sr-only">Produtos por nível</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          v-for="level in LEVELS"
          :key="level"
          :title="STOCK_LEVELS[level].label"
          :tone="STOCK_LEVELS[level].tone"
          :value="summary.data.value?.por_nivel?.[level] ?? '—'"
          :loading="summary.loading.value"
          :active="nivel === level"
          :to="cardTarget(level)"
        />
      </div>
      <ErrorState
        v-if="summary.error.value && !summary.loading.value"
        message="Não foi possível carregar as contagens por nível."
        @retry="summary.load"
      />
    </section>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <BaseTable
      v-else
      caption="Produtos em alerta de estoque"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="
        nivel === '' && !showOk ? 'Nenhum produto em alerta. Tudo dentro do colchão.' : 'Nenhum produto neste filtro'
      "
      :empty-description="nivel === '' && !showOk ? '' : 'Escolha outro nível ou limpe o filtro.'"
    >
      <template #cell-name="{ row }">
        <span class="font-medium text-slate-800">{{ row.name }}</span>
        <span v-if="categoryOf(row)" class="block text-xs text-slate-500">{{ categoryOf(row) }}</span>
      </template>
      <template #cell-nivel="{ row }"><StockLevelBadge :level="row.nivel" /></template>
      <template #cell-current_stock="{ row }">{{ formatQuantity(row.current_stock, row.unit) }}</template>
      <template #cell-min_stock="{ row }">{{ formatQuantity(row.min_stock, row.unit) }}</template>
      <template #cell-daily_consumption="{ row }">
        {{ row.daily_consumption ? formatQuantity(row.daily_consumption, row.unit) : '—' }}
      </template>
      <template #cell-cobertura_dias="{ row }">{{ coverage(row) }}</template>
      <template #cell-reposicao="{ row }">{{ restock(row) }}</template>
      <template #cell-actions="{ row }">
        <div class="flex items-center gap-3 whitespace-nowrap">
          <RouterLink
            :to="{ name: 'movimentacoes', query: { produto: row.id, tipo: 'entrada' } }"
            class="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
            :aria-label="`Registrar entrada de ${row.name}`"
          >
            Registrar entrada
          </RouterLink>
          <RouterLink
            :to="{ name: 'produtos', query: { q: row.name } }"
            :class="linkClass"
            :aria-label="`Ver produto ${row.name}`"
          >
            Ver produto
          </RouterLink>
        </div>
      </template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />
  </div>
</template>
