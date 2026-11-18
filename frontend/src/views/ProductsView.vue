<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listCategories } from '../api/categories'
import { listProducts, updateProduct } from '../api/products'
import { listSuppliers } from '../api/suppliers'
import ProductFormModal from '../components/domain/ProductFormModal.vue'
import StockLevelBadge from '../components/domain/StockLevelBadge.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import { STOCK_LEVELS } from '../utils/constants'
import { formatDecimal, formatQuantity } from '../utils/format'

const PER_PAGE = 10
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

// ---- Filtros: a URL (query) é a fonte da verdade -------------------------
const q = computed(() => String(route.query.q ?? ''))
const categoria = computed(() => String(route.query.categoria ?? ''))
const nivel = computed(() => (route.query.nivel in STOCK_LEVELS ? String(route.query.nivel) : ''))
const situacao = computed(() => (['inativos', 'todos'].includes(route.query.situacao) ? route.query.situacao : 'ativos'))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(q.value || categoria.value || nivel.value || situacao.value !== 'ativos'))

function setQuery(patch, { replace = false, keepPage = false } = {}) {
  const next = { ...route.query, ...patch }
  if (!keepPage) delete next.page
  for (const key of Object.keys(next)) {
    if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
  }
  if (next.situacao === 'ativos') delete next.situacao
  if (next.page === 1) delete next.page
  return router[replace ? 'replace' : 'push']({ query: next })
}

const search = ref(q.value)
let debounceId = null
watch(search, (value) => {
  clearTimeout(debounceId)
  debounceId = setTimeout(() => {
    if (value.trim() !== q.value) setQuery({ q: value.trim() }, { replace: true })
  }, 300)
})
watch(q, (value) => {
  if (value !== search.value.trim()) search.value = value // voltar/avançar no navegador
})

const levelOptions = Object.entries(STOCK_LEVELS).map(([value, { label }]) => ({ value, label }))
const situationOptions = [
  { value: 'ativos', label: 'Ativos' },
  { value: 'inativos', label: 'Inativos' },
  { value: 'todos', label: 'Todos' },
]

function clearFilters() {
  clearTimeout(debounceId)
  search.value = ''
  router.push({ query: {} })
}

// ---- Categorias e fornecedores (carregados uma vez enquanto a view existe) --
const categories = useAsyncBlock(() => listCategories({ per_page: 100 }))
const suppliers = useAsyncBlock(() => listSuppliers({ per_page: 100 }))
const categoryList = computed(() => categories.data.value?.items ?? [])
const supplierList = computed(() => suppliers.data.value?.items ?? [])
const categoryNames = computed(() => new Map(categoryList.value.map((c) => [c.id, c.name])))
const supplierNames = computed(() => new Map(supplierList.value.map((s) => [s.id, s.name])))
const categoryFilterOptions = computed(() => categoryList.value.map((c) => ({ value: c.id, label: c.name })))
const refsLoading = computed(() => categories.loading.value || suppliers.loading.value)
const refsError = computed(() => categories.error.value || suppliers.error.value)

function loadRefs() {
  if (!categories.data.value) categories.load()
  if (!suppliers.data.value) suppliers.load()
}

// ---- Listagem ---------------------------------------------------------------
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestId = 0

// A API não filtra por nível: nesse caso busca todas as páginas e filtra/pagina aqui.
async function fetchAllByLevel(base) {
  const all = []
  let p = 1
  for (;;) {
    const res = await listProducts({ ...base, page: p, per_page: 100 })
    all.push(...res.items)
    if (!res.items.length || all.length >= res.total) break
    p++
  }
  const filtered = all.filter((item) => item.nivel === nivel.value)
  const start = (page.value - 1) * PER_PAGE
  return { items: filtered.slice(start, start + PER_PAGE), total: filtered.length }
}

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  const base = {
    search: q.value || undefined,
    category_id: categoria.value || undefined,
    active: situacao.value === 'todos' ? undefined : situacao.value === 'ativos',
  }
  try {
    const res = nivel.value
      ? await fetchAllByLevel(base)
      : await listProducts({ ...base, page: page.value, per_page: PER_PAGE })
    if (id !== requestId) return // resposta antiga: descarta
    rows.value = res.items
    total.value = res.total
    // Página fora do intervalo (ex.: depois de desativar o último item da última página)
    if (!res.items.length && res.total > 0 && page.value > 1) {
      setQuery({ page: Math.ceil(res.total / PER_PAGE) }, { replace: true, keepPage: true })
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
    if (route.name === 'produtos') load()
  },
)
onMounted(() => {
  loadRefs()
  load()
})

// ---- Tabela -----------------------------------------------------------------
const columns = computed(() => [
  { key: 'name', label: 'Produto' },
  { key: 'category_id', label: 'Categoria' },
  { key: 'supplier_id', label: 'Fornecedor' },
  { key: 'current_stock', label: 'Estoque atual' },
  { key: 'min_stock', label: 'Mínimo' },
  { key: 'cobertura_dias', label: 'Cobertura' },
  { key: 'nivel', label: 'Nível' },
  { key: 'active', label: 'Situação' },
  ...(auth.isAdmin ? [{ key: 'actions', label: 'Ações' }] : []),
])
const coverage = (row) =>
  row.cobertura_dias === null || row.cobertura_dias === undefined
    ? '—'
    : `${formatDecimal(row.cobertura_dias)} dia(s)`

// ---- Criar / editar ---------------------------------------------------------
const formOpen = ref(false)
const editing = ref(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(row) {
  editing.value = row
  formOpen.value = true
}

// ---- Desativar / reativar -----------------------------------------------------
const confirmOpen = ref(false)
const target = ref(null)
const toggling = ref(false)

function askDeactivate(row) {
  target.value = row
  confirmOpen.value = true
}

async function setActive(row, active) {
  if (toggling.value) return
  toggling.value = true
  try {
    await updateProduct(row.id, { active })
    toast.success(active ? 'Produto reativado.' : 'Produto desativado.')
    confirmOpen.value = false
    await load()
  } catch (err) {
    toast.error(err.status === 403 ? 'Você não tem permissão para alterar produtos.' : err.message)
  } finally {
    toggling.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Cadastro de produtos e situação do estoque.</p>
      <BaseButton v-if="auth.isAdmin" @click="openCreate">Novo produto</BaseButton>
    </div>

    <!-- Filtros -->
    <form
      class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-5"
      role="search"
      @submit.prevent
    >
      <div class="lg:col-span-2">
        <BaseInput v-model="search" label="Buscar" type="search" placeholder="Nome ou código" />
      </div>
      <BaseSelect
        label="Categoria"
        placeholder="Todas"
        :model-value="categoria"
        :options="categoryFilterOptions"
        @update:model-value="setQuery({ categoria: $event })"
      />
      <BaseSelect
        label="Nível"
        placeholder="Todos"
        :model-value="nivel"
        :options="levelOptions"
        @update:model-value="setQuery({ nivel: $event })"
      />
      <BaseSelect
        label="Situação"
        :model-value="situacao"
        :options="situationOptions"
        @update:model-value="setQuery({ situacao: $event })"
      />
      <div class="sm:col-span-2 lg:col-span-5">
        <BaseButton variant="secondary" size="sm" :disabled="!hasFilters && !search" @click="clearFilters">
          Limpar filtros
        </BaseButton>
      </div>
    </form>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <BaseTable
      v-else
      caption="Lista de produtos"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhum resultado para os filtros' : 'Nenhum produto cadastrado'"
      :empty-description="
        hasFilters
          ? 'Ajuste ou limpe os filtros para ver outros produtos.'
          : auth.isAdmin
            ? 'Use “Novo produto” para cadastrar o primeiro.'
            : 'O administrador ainda não cadastrou produtos.'
      "
    >
      <template #cell-name="{ row }">
        <span class="font-medium text-slate-800">{{ row.name }}</span>
        <span v-if="row.code" class="block text-xs text-slate-500">{{ row.code }}</span>
      </template>
      <template #cell-category_id="{ value }">{{ categoryNames.get(value) ?? '—' }}</template>
      <template #cell-supplier_id="{ value }">{{ supplierNames.get(value) ?? '—' }}</template>
      <template #cell-current_stock="{ row }">{{ formatQuantity(row.current_stock, row.unit) }}</template>
      <template #cell-min_stock="{ row }">{{ formatQuantity(row.min_stock, row.unit) }}</template>
      <template #cell-cobertura_dias="{ row }">{{ coverage(row) }}</template>
      <template #cell-nivel="{ row }"><StockLevelBadge :level="row.nivel" /></template>
      <template #cell-active="{ row }">
        <BaseBadge :tone="row.active ? 'emerald' : 'slate'">{{ row.active ? 'Ativo' : 'Inativo' }}</BaseBadge>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex gap-2 whitespace-nowrap">
          <BaseButton variant="secondary" size="sm" :aria-label="`Editar ${row.name}`" @click="openEdit(row)">
            Editar
          </BaseButton>
          <BaseButton
            v-if="row.active"
            variant="danger"
            size="sm"
            :aria-label="`Desativar ${row.name}`"
            @click="askDeactivate(row)"
          >
            Desativar
          </BaseButton>
          <BaseButton
            v-else
            size="sm"
            :disabled="toggling"
            :aria-label="`Reativar ${row.name}`"
            @click="setActive(row, true)"
          >
            Reativar
          </BaseButton>
        </div>
      </template>
    </BaseTable>

    <BasePagination
      :page="page"
      :per-page="PER_PAGE"
      :total="total"
      @update:page="setQuery({ page: $event }, { keepPage: true })"
    />

    <ProductFormModal
      v-model="formOpen"
      :product="editing"
      :categories="categoryList"
      :suppliers="supplierList"
      :refs-loading="refsLoading"
      :refs-error="refsError"
      @retry-refs="loadRefs"
      @saved="load"
    />
    <ConfirmDialog
      v-model="confirmOpen"
      danger
      title="Desativar produto?"
      :message="`Ele deixa de aparecer nas listas ativas, mas o histórico é mantido.${target ? ` (${target.name})` : ''}`"
      confirm-label="Desativar"
      :loading="toggling"
      @confirm="setActive(target, false)"
    />
  </div>
</template>
