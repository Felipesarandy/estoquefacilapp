<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDashboard } from '../api/dashboard'
import { listMovements } from '../api/movements'
import { listAllProducts } from '../api/products'
import { listUsers } from '../api/users'
import MovementFormModal from '../components/domain/MovementFormModal.vue'
import ProductSelect from '../components/domain/ProductSelect.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import { ENTRY_REASONS, EXIT_REASONS, MOVEMENT_REASONS, MOVEMENT_TYPES } from '../utils/constants'
import { formatCurrency, formatDate, formatDateTime, formatQuantity } from '../utils/format'

const PER_PAGE = 10
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

// ---- Filtros na URL (?produto= e ?tipo= ficam reservados para abrir o modal) --------
const fProduto = computed(() => String(route.query.f_produto ?? ''))
const fTipo = computed(() => (route.query.f_tipo in MOVEMENT_TYPES ? String(route.query.f_tipo) : ''))
const fMotivo = computed(() => (route.query.f_motivo in MOVEMENT_REASONS ? String(route.query.f_motivo) : ''))
const de = computed(() => String(route.query.de ?? ''))
const ate = computed(() => String(route.query.ate ?? ''))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(fProduto.value || fTipo.value || fMotivo.value || de.value || ate.value))
const dateError = computed(() => (de.value && ate.value && de.value > ate.value ? 'A data final deve ser igual ou posterior à inicial.' : ''))

function setQuery(patch, { keepPage = false } = {}) {
  const next = { ...route.query, ...patch }
  if (!keepPage) delete next.page
  for (const key of Object.keys(next)) {
    if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
  }
  if (next.page === 1) delete next.page
  return router.push({ query: next })
}

const typeOptions = Object.entries(MOVEMENT_TYPES).map(([value, label]) => ({ value, label }))
const reasonOptions = [...new Set([...ENTRY_REASONS, ...EXIT_REASONS])].map((r) => ({ value: r, label: MOVEMENT_REASONS[r] }))

// ---- Dados de apoio ------------------------------------------------------------------
const products = useAsyncBlock(() => listAllProducts()) // todos, inclusive inativos
const dashboard = useAsyncBlock(getDashboard)
const users = useAsyncBlock(() => listUsers({ per_page: 100 })) // só admin
const productList = computed(() => products.data.value ?? [])
const productMap = computed(() => new Map(productList.value.map((p) => [p.id, p])))
const userNames = computed(() => new Map((users.data.value?.items ?? []).map((u) => [u.id, u.name])))
const daysAhead = computed(() => dashboard.data.value?.dias_antecedencia ?? 5)

function userLabel(id) {
  if (id === auth.user?.id) return 'Você'
  return userNames.value.get(id) ?? `Usuário #${id}`
}

// ---- Lista ---------------------------------------------------------------------------
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestId = 0

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
    const res = await listMovements({
      product_id: fProduto.value || undefined,
      type: fTipo.value || undefined,
      reason: fMotivo.value || undefined,
      from: de.value || undefined,
      to: ate.value || undefined,
      page: page.value,
      per_page: PER_PAGE,
    })
    if (id !== requestId) return // resposta antiga
    rows.value = res.items
    total.value = res.total
    if (!res.items.length && res.total > 0 && page.value > 1) {
      router.replace({ query: { ...route.query, page: Math.ceil(res.total / PER_PAGE) } })
    }
  } catch (err) {
    if (id !== requestId) return
    error.value = err.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(
  () => route.query,
  () => {
    if (route.name === 'movimentacoes') load()
  },
)

// ---- Modal de registro -----------------------------------------------------------------
const formOpen = ref(false)
const initialProduct = ref('')
const initialType = ref('entrada')

function openForm(type, productId = '') {
  initialType.value = type
  initialProduct.value = productId
  formOpen.value = true
}

// Vindo de Alertas: ?produto=<id>&tipo=entrada abre o modal e limpa esses parâmetros.
async function handleLaunch() {
  const { produto, tipo } = route.query
  if (produto === undefined && tipo === undefined) return
  const rest = { ...route.query }
  delete rest.produto
  delete rest.tipo
  router.replace({ query: rest })

  if (produto === undefined) return openForm(tipo === 'saida' ? 'saida' : 'entrada')
  const target = productMap.value.get(Number(produto))
  if (!target) toast.warning('Produto não encontrado para registrar a movimentação.')
  else if (!target.active) toast.warning('Produto inativo não pode receber movimentações.')
  else openForm(tipo === 'saida' ? 'saida' : 'entrada', String(target.id))
}

function onSaved() {
  products.load() // saldos mudaram
  if (page.value !== 1) setQuery({}) // volta à página 1 mantendo os filtros
  else load()
}

onMounted(async () => {
  load()
  dashboard.load()
  if (auth.isAdmin) users.load()
  await products.load()
  await handleLaunch()
})

// ---- Tabela ---------------------------------------------------------------------------
const columns = [
  { key: 'created_at', label: 'Data/hora' },
  { key: 'product_id', label: 'Produto' },
  { key: 'type', label: 'Tipo' },
  { key: 'reason', label: 'Motivo' },
  { key: 'quantity', label: 'Quantidade' },
  { key: 'unit_cost', label: 'Custo unitário' },
  { key: 'batch', label: 'Lote' },
  { key: 'expiration_date', label: 'Validade' },
  { key: 'note', label: 'Observação' },
  { key: 'user_id', label: 'Usuário' },
]
const productName = (id) => productMap.value.get(id)?.name ?? `Produto #${id}`
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="max-w-2xl text-sm text-slate-600">
        Movimentações não podem ser editadas nem excluídas. Para corrigir um lançamento, registre uma movimentação de
        ajuste.
      </p>
      <div class="flex gap-2">
        <BaseButton @click="openForm('entrada')">Registrar entrada</BaseButton>
        <BaseButton variant="secondary" @click="openForm('saida')">Registrar saída</BaseButton>
      </div>
    </div>

    <!-- Filtros -->
    <form class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-4" role="search" @submit.prevent>
      <div class="sm:col-span-2">
        <ProductSelect
          label="Produto"
          placeholder="Todos"
          :model-value="fProduto"
          :products="productList"
          @update:model-value="setQuery({ f_produto: $event })"
        />
      </div>
      <BaseSelect label="Tipo" placeholder="Todos" :model-value="fTipo" :options="typeOptions" @update:model-value="setQuery({ f_tipo: $event })" />
      <BaseSelect label="Motivo" placeholder="Todos" :model-value="fMotivo" :options="reasonOptions" @update:model-value="setQuery({ f_motivo: $event })" />
      <BaseInput label="De" type="date" :model-value="de" @update:model-value="setQuery({ de: $event })" />
      <BaseInput label="Até" type="date" :model-value="ate" :error="dateError" @update:model-value="setQuery({ ate: $event })" />
      <div class="flex items-end sm:col-span-2">
        <BaseButton variant="secondary" size="sm" :disabled="!hasFilters" @click="router.push({ query: {} })">Limpar filtros</BaseButton>
      </div>
    </form>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <BaseTable
      v-else
      caption="Histórico de movimentações"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhuma movimentação para os filtros' : 'Nenhuma movimentação registrada'"
      :empty-description="hasFilters ? 'Ajuste ou limpe os filtros.' : 'Use “Registrar entrada” ou “Registrar saída”.'"
    >
      <template #cell-created_at="{ value }"><span class="whitespace-nowrap">{{ formatDateTime(value) }}</span></template>
      <template #cell-product_id="{ value }">{{ productName(value) }}</template>
      <template #cell-type="{ value }">
        <BaseBadge :tone="value === 'entrada' ? 'emerald' : 'rose'">{{ MOVEMENT_TYPES[value] ?? value }}</BaseBadge>
      </template>
      <template #cell-reason="{ value }">{{ MOVEMENT_REASONS[value] ?? value }}</template>
      <template #cell-quantity="{ row }">
        <span class="whitespace-nowrap">{{ formatQuantity(row.quantity, productMap.get(row.product_id)?.unit) }}</span>
      </template>
      <template #cell-unit_cost="{ value }">{{ value ? formatCurrency(value) : '—' }}</template>
      <template #cell-batch="{ value }">{{ value || '—' }}</template>
      <template #cell-expiration_date="{ value }">{{ value ? formatDate(value) : '—' }}</template>
      <template #cell-note="{ value }">
        <span v-if="value" class="block max-w-[14rem] truncate" :title="value">{{ value }}</span>
        <span v-else>—</span>
      </template>
      <template #cell-user_id="{ value }">{{ userLabel(value) }}</template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />

    <MovementFormModal
      v-model="formOpen"
      :products="productList"
      :initial-product="initialProduct"
      :initial-type="initialType"
      :days-ahead="daysAhead"
      @saved="onSaved"
      @conflict="products.load"
    />
  </div>
</template>
