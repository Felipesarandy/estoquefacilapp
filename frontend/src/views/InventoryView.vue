<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { listInventory } from '../api/inventory'
import { listAllProducts } from '../api/products'
import { listUsers } from '../api/users'
import InventoryDetailModal from '../components/domain/InventoryDetailModal.vue'
import InventoryFormModal from '../components/domain/InventoryFormModal.vue'
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
import { INVENTORY_RESULTS } from '../utils/constants'
import { formatDateTime, formatQuantity } from '../utils/format'
import { differenceClass, signedDecimal } from '../utils/inventory'

const PER_PAGE = 10
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// ---- Filtros na URL: ?produto=&resultado=&de=&ate=&page= -----------------------------------------
const produto = computed(() => String(route.query.produto ?? ''))
const resultado = computed(() => (route.query.resultado in INVENTORY_RESULTS ? String(route.query.resultado) : ''))
const de = computed(() => String(route.query.de ?? ''))
const ate = computed(() => String(route.query.ate ?? ''))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(produto.value || resultado.value || de.value || ate.value))
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
const resultOptions = Object.entries(INVENTORY_RESULTS).map(([value, label]) => ({ value, label }))

// ---- Apoio -------------------------------------------------------------------------------------------
const products = useAsyncBlock(() => listAllProducts()) // todos, inclusive inativos
const users = useAsyncBlock(() => listUsers({ per_page: 100 })) // só admin
const productList = computed(() => products.data.value ?? [])
const productMap = computed(() => new Map(productList.value.map((p) => [p.id, p])))
const userNames = computed(() => new Map((users.data.value?.items ?? []).map((u) => [u.id, u.name])))
const userLabel = (id) => userNames.value.get(id) ?? `Usuário #${id}`

// ---- Lista ---------------------------------------------------------------------------------------------
// A API filtra produto e período, mas não "divergência": nesse caso busca tudo e filtra/pagina aqui.
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestId = 0

async function fetchAll(params) {
  const all = []
  for (let p = 1; ; p++) {
    const res = await listInventory({ ...params, page: p, per_page: 100 })
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
  const base = { product_id: produto.value || undefined, from: de.value || undefined, to: ate.value || undefined }
  try {
    let items
    let count
    if (resultado.value) {
      const filtered = (await fetchAll(base)).filter((c) => (Number(c.difference) !== 0) === (resultado.value === 'divergencia'))
      count = filtered.length
      const start = (page.value - 1) * PER_PAGE
      items = filtered.slice(start, start + PER_PAGE)
    } else {
      const res = await listInventory({ ...base, page: page.value, per_page: PER_PAGE })
      items = res.items
      count = res.total
    }
    if (id !== requestId) return // resposta antiga
    rows.value = items
    total.value = count
    if (!items.length && count > 0 && page.value > 1) {
      router.replace({ query: { ...route.query, page: Math.ceil(count / PER_PAGE) } })
    }
  } catch (err) {
    if (id !== requestId) return
    error.value = err.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

function refreshAll() {
  products.load()
  load()
}
function onSaved() {
  products.load() // saldos mudaram
  if (page.value !== 1) setQuery({}) // volta à página 1 mantendo os filtros
  else load()
}

watch(
  () => route.query,
  () => {
    if (route.name === 'inventario') load()
  },
)
onMounted(() => {
  products.load()
  if (auth.isAdmin) users.load()
  load()
})

// ---- Modais ----------------------------------------------------------------------------------------------
const formOpen = ref(false)
const detailOpen = ref(false)
const selected = ref(null)
function openDetail(row) {
  selected.value = row
  detailOpen.value = true
}

const columns = computed(() => [
  { key: 'created_at', label: 'Data/hora' },
  { key: 'product_id', label: 'Produto' },
  { key: 'system_quantity', label: 'Saldo do sistema' },
  { key: 'counted_quantity', label: 'Contado' },
  { key: 'difference', label: 'Diferença' },
  { key: 'result', label: 'Resultado' },
  ...(auth.isAdmin ? [{ key: 'user_id', label: 'Usuário' }] : []),
  { key: 'actions', label: 'Detalhes' },
])
const unitOf = (id) => productMap.value.get(id)?.unit
</script>

<template>
  <div class="space-y-5">
    <p class="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
      Compare a contagem física com o saldo do sistema. Se houver diferença, o saldo é corrigido por uma movimentação de
      ajuste e um incidente de divergência é aberto.
    </p>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <BaseButton variant="secondary" size="sm" :loading="loading" @click="refreshAll">Atualizar</BaseButton>
      <BaseButton @click="formOpen = true">Nova contagem</BaseButton>
    </div>

    <form class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-4" role="search" @submit.prevent>
      <div class="sm:col-span-2">
        <ProductSelect label="Produto" placeholder="Todos" :model-value="produto" :products="productList" @update:model-value="setQuery({ produto: $event })" />
      </div>
      <BaseSelect label="Resultado" placeholder="Todos" :model-value="resultado" :options="resultOptions" @update:model-value="setQuery({ resultado: $event })" />
      <div class="hidden lg:block" />
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
      caption="Contagens de inventário"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhuma contagem para os filtros' : 'Nenhuma contagem registrada'"
      :empty-description="hasFilters ? 'Ajuste ou limpe os filtros.' : 'Use “Nova contagem” para registrar a primeira.'"
    >
      <template #cell-created_at="{ value }"><span class="whitespace-nowrap">{{ formatDateTime(value) }}</span></template>
      <template #cell-product_id="{ value }">
        <RouterLink v-if="productMap.get(value)" :to="{ name: 'produtos', query: { q: productMap.get(value).name } }" class="text-emerald-700 hover:underline">
          {{ productMap.get(value).name }}
        </RouterLink>
        <span v-else>Produto #{{ value }}</span>
      </template>
      <template #cell-system_quantity="{ row }">{{ formatQuantity(row.system_quantity, unitOf(row.product_id)) }}</template>
      <template #cell-counted_quantity="{ row }">{{ formatQuantity(row.counted_quantity, unitOf(row.product_id)) }}</template>
      <template #cell-difference="{ row }">
        <span class="whitespace-nowrap font-semibold" :class="differenceClass(row.difference)">
          {{ signedDecimal(row.difference) }}
          <span class="text-xs font-normal">{{ Number(row.difference) > 0 ? 'sobra' : Number(row.difference) < 0 ? 'falta' : '' }}</span>
        </span>
      </template>
      <template #cell-result="{ row }">
        <BaseBadge :tone="Number(row.difference) === 0 ? 'emerald' : 'orange'">{{ Number(row.difference) === 0 ? 'Sem divergência' : 'Divergência' }}</BaseBadge>
      </template>
      <template #cell-user_id="{ value }">{{ userLabel(value) }}</template>
      <template #cell-actions="{ row }">
        <BaseButton variant="secondary" size="sm" :aria-label="`Detalhes da contagem ${row.id}`" @click="openDetail(row)">Detalhes</BaseButton>
      </template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />

    <InventoryFormModal v-model="formOpen" :products="productList" @saved="onSaved" @conflict="products.load" />
    <InventoryDetailModal
      v-model="detailOpen"
      :count="selected"
      :product="selected ? productMap.get(selected.product_id) ?? null : null"
      :user-label="selected && auth.isAdmin ? userLabel(selected.user_id) : ''"
    />
  </div>
</template>
