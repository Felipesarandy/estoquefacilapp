<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { getIncidentsSummary, listIncidents } from '../api/incidents'
import { listAllProducts } from '../api/products'
import { listUsers } from '../api/users'
import IncidentDetailModal from '../components/domain/IncidentDetailModal.vue'
import IncidentFormModal from '../components/domain/IncidentFormModal.vue'
import ProductSelect from '../components/domain/ProductSelect.vue'
import StatCard from '../components/domain/StatCard.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { useAuthStore } from '../stores/auth'
import { INCIDENT_SEVERITY, INCIDENT_STATUS, INCIDENT_TYPES } from '../utils/constants'
import { formatDateTime, formatDecimal } from '../utils/format'

const PER_PAGE = 10
const STATUSES = Object.keys(INCIDENT_STATUS) // aberto, em_analise, resolvido, fechado
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// ---- Filtros na URL: ?status=&gravidade=&produto=&de=&ate=&page= --------------------------
// status: "ativos" (padrão = não fechados), "todos" ou um status específico.
const status = computed(() => (route.query.status === 'todos' || STATUSES.includes(route.query.status) ? String(route.query.status) : 'ativos'))
const gravidade = computed(() => (route.query.gravidade in INCIDENT_SEVERITY ? String(route.query.gravidade) : ''))
const produto = computed(() => String(route.query.produto ?? ''))
const de = computed(() => String(route.query.de ?? ''))
const ate = computed(() => String(route.query.ate ?? ''))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(status.value !== 'ativos' || gravidade.value || produto.value || de.value || ate.value))
const dateError = computed(() => (de.value && ate.value && de.value > ate.value ? 'A data final deve ser igual ou posterior à inicial.' : ''))

function setQuery(patch, { keepPage = false } = {}) {
  const next = { ...route.query, ...patch }
  if (!keepPage) delete next.page
  for (const key of Object.keys(next)) {
    if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
  }
  if (next.status === 'ativos') delete next.status
  if (next.page === 1) delete next.page
  return router.push({ query: next })
}

const statusOptions = [
  { value: 'ativos', label: 'Não fechados' },
  { value: 'todos', label: 'Todos' },
  ...STATUSES.map((s) => ({ value: s, label: INCIDENT_STATUS[s].label })),
]
const severityOptions = Object.entries(INCIDENT_SEVERITY).map(([value, { label }]) => ({ value, label }))

// ---- Apoio: resumo, produtos e (admin) usuários -------------------------------------------------
const summary = useAsyncBlock(getIncidentsSummary)
const products = useAsyncBlock(() => listAllProducts())
const users = useAsyncBlock(() => listUsers({ per_page: 100 }))
const productList = computed(() => products.data.value ?? [])
const productMap = computed(() => new Map(productList.value.map((p) => [p.id, p])))
const userNames = computed(() => new Map((users.data.value?.items ?? []).map((u) => [u.id, u.name])))

// ---- Lista --------------------------------------------------------------------------------------
// A API filtra um único status, tipo e produto, mas não gravidade, período nem "não fechados":
// busca tudo (com status/produto específicos, se houver) e filtra/pagina aqui.
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestId = 0

async function fetchAll(params) {
  const all = []
  for (let p = 1; ; p++) {
    const res = await listIncidents({ ...params, page: p, per_page: 100 })
    all.push(...res.items)
    if (!res.items.length || all.length >= res.total) return all
  }
}

async function load() {
  const id = ++requestId
  if (dateError.value) {
    rows.value = []
    total.value = 0
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const all = await fetchAll({
      status: STATUSES.includes(status.value) ? status.value : undefined,
      product_id: produto.value || undefined,
    })
    if (id !== requestId) return // resposta antiga
    const filtered = all.filter(
      (i) =>
        (status.value !== 'ativos' || i.status !== 'fechado') &&
        (!gravidade.value || i.severity === gravidade.value) &&
        (!de.value || i.opened_at.slice(0, 10) >= de.value) &&
        (!ate.value || i.opened_at.slice(0, 10) <= ate.value),
    ) // a API já devolve do mais recente para o mais antigo
    const start = (page.value - 1) * PER_PAGE
    rows.value = filtered.slice(start, start + PER_PAGE)
    total.value = filtered.length
    if (!rows.value.length && filtered.length && page.value > 1) {
      router.replace({ query: { ...route.query, page: Math.ceil(filtered.length / PER_PAGE) } })
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
}
function onChanged() {
  refreshAll()
  products.load() // nível do produto pode ter mudado
}

watch(
  () => route.query,
  () => {
    if (route.name === 'incidentes') load()
  },
)
onMounted(() => {
  summary.load()
  products.load()
  if (auth.isAdmin) users.load()
  load()
})

// ---- Cartões de resumo --------------------------------------------------------------------------
const countOf = (s) => summary.data.value?.por_status?.[s] ?? 0
const avgHours = computed(() => summary.data.value?.tempo_medio_resolucao_horas)

// ---- Detalhe e criação -----------------------------------------------------------------------------
const detailOpen = ref(false)
const detailId = ref(null)
function openDetail(row) {
  detailId.value = row.id
  detailOpen.value = true
}
const formOpen = ref(false)

const columns = [
  { key: 'id', label: 'Nº' },
  { key: 'type', label: 'Incidente' },
  { key: 'product_id', label: 'Produto' },
  { key: 'severity', label: 'Gravidade' },
  { key: 'status', label: 'Status' },
  { key: 'opened_at', label: 'Aberto em' },
  { key: 'closed_at', label: 'Encerrado em' },
  { key: 'actions', label: 'Ações' },
]
</script>

<template>
  <div class="space-y-5">
    <p class="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
      Incidentes são abertos automaticamente quando um produto entra em ruptura ou quando o inventário encontra
      divergência (também podem ser abertos manualmente), e acompanham o ciclo: aberto, em análise, resolvido e fechado.
    </p>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <BaseButton variant="secondary" size="sm" :loading="loading || summary.loading.value" @click="refreshAll">Atualizar</BaseButton>
      <BaseButton @click="formOpen = true">Novo incidente</BaseButton>
    </div>

    <!-- Resumo por status: clicar filtra -->
    <section aria-labelledby="titulo-resumo">
      <h2 id="titulo-resumo" class="sr-only">Incidentes por status</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          v-for="s in STATUSES"
          :key="s"
          :title="INCIDENT_STATUS[s].label"
          :tone="INCIDENT_STATUS[s].tone"
          :value="summary.data.value ? countOf(s) : '—'"
          :loading="summary.loading.value"
          :active="status === s"
          :to="{ name: 'incidentes', query: { ...route.query, page: undefined, status: status === s ? undefined : s } }"
        />
      </div>
      <p v-if="avgHours" class="mt-2 text-xs text-slate-500">Tempo médio de resolução: {{ formatDecimal(avgHours, 1) }} h.</p>
      <ErrorState v-if="summary.error.value && !summary.loading.value" message="Não foi possível carregar o resumo." @retry="summary.load" />
    </section>

    <!-- Filtros -->
    <form class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-4" role="search" @submit.prevent>
      <BaseSelect label="Status" :model-value="status" :options="statusOptions" @update:model-value="setQuery({ status: $event })" />
      <BaseSelect label="Gravidade" placeholder="Todas" :model-value="gravidade" :options="severityOptions" @update:model-value="setQuery({ gravidade: $event })" />
      <div class="sm:col-span-2">
        <ProductSelect label="Produto" placeholder="Todos" :model-value="produto" :products="productList" @update:model-value="setQuery({ produto: $event })" />
      </div>
      <BaseInput label="Aberto de" type="date" :model-value="de" @update:model-value="setQuery({ de: $event })" />
      <BaseInput label="Aberto até" type="date" :model-value="ate" :error="dateError" @update:model-value="setQuery({ ate: $event })" />
      <div class="flex items-end sm:col-span-2">
        <BaseButton variant="secondary" size="sm" :disabled="!hasFilters" @click="router.push({ query: {} })">Limpar filtros</BaseButton>
      </div>
    </form>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <BaseTable
      v-else
      caption="Lista de incidentes"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhum incidente para os filtros' : 'Nenhum incidente em andamento'"
      :empty-description="hasFilters ? 'Ajuste ou limpe os filtros.' : 'Tudo certo por aqui.'"
    >
      <template #cell-id="{ value }">#{{ value }}</template>
      <template #cell-type="{ row }">
        <span class="font-medium text-slate-800">{{ INCIDENT_TYPES[row.type] ?? row.type }}</span>
        <span class="block max-w-[16rem] truncate text-xs text-slate-500" :title="row.description">{{ row.description }}</span>
      </template>
      <template #cell-product_id="{ row }">
        <RouterLink
          v-if="row.product_id && productMap.get(row.product_id)"
          :to="{ name: 'produtos', query: { q: productMap.get(row.product_id).name } }"
          class="text-emerald-700 hover:underline"
        >
          {{ productMap.get(row.product_id).name }}
        </RouterLink>
        <span v-else>{{ row.product_id ? `Produto #${row.product_id}` : '—' }}</span>
      </template>
      <template #cell-severity="{ value }">
        <BaseBadge :custom-class="INCIDENT_SEVERITY[value]?.classes">{{ INCIDENT_SEVERITY[value]?.label ?? value }}</BaseBadge>
      </template>
      <template #cell-status="{ value }">
        <BaseBadge :custom-class="INCIDENT_STATUS[value]?.classes">{{ INCIDENT_STATUS[value]?.label ?? value }}</BaseBadge>
      </template>
      <template #cell-opened_at="{ value }"><span class="whitespace-nowrap">{{ formatDateTime(value) }}</span></template>
      <template #cell-closed_at="{ value }"><span class="whitespace-nowrap">{{ value ? formatDateTime(value) : '—' }}</span></template>
      <template #cell-actions="{ row }">
        <BaseButton variant="secondary" size="sm" :aria-label="`Detalhes do incidente ${row.id}`" @click="openDetail(row)">Detalhes</BaseButton>
      </template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />

    <IncidentDetailModal v-model="detailOpen" :incident-id="detailId" :products="productMap" :user-names="userNames" @changed="onChanged" />
    <IncidentFormModal v-model="formOpen" :products="productList" @saved="onChanged" />
  </div>
</template>
