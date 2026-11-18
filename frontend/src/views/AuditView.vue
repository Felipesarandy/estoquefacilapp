<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { listAudit } from '../api/audit'
import { listUsers } from '../api/users'
import AuditDetailModal from '../components/domain/AuditDetailModal.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { useToastStore } from '../stores/toast'
import { AUDIT_ACTIONS, AUDIT_ENTITIES, AUDIT_ENTITY_ROUTES } from '../utils/constants'
import { formatDateTime, formatTime } from '../utils/format'

const PER_PAGE = 20
const route = useRoute()
const router = useRouter()
const toast = useToastStore()

// ---- Filtros na URL (?entidade=&id=&acao=&usuario=&de=&ate=&page=) -> API (entity, entity_id, ...) ----
const entidade = computed(() => (route.query.entidade in AUDIT_ENTITIES ? String(route.query.entidade) : ''))
const entityId = computed(() => (/^\d+$/.test(String(route.query.id ?? '')) ? String(route.query.id) : ''))
const acao = computed(() => (route.query.acao in AUDIT_ACTIONS ? String(route.query.acao) : ''))
const usuario = computed(() => String(route.query.usuario ?? ''))
const de = computed(() => String(route.query.de ?? ''))
const ate = computed(() => String(route.query.ate ?? ''))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(entidade.value || entityId.value || acao.value || usuario.value || de.value || ate.value))
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

const entityOptions = Object.entries(AUDIT_ENTITIES).map(([value, label]) => ({ value, label }))
const actionOptions = Object.entries(AUDIT_ACTIONS).map(([value, { label }]) => ({ value, label }))

// ---- Usuários (a API não devolve o nome no registro) ---------------------------------------------
const users = useAsyncBlock(() => listUsers({ per_page: 100 }))
const userList = computed(() => users.data.value?.items ?? [])
const userNames = computed(() => new Map(userList.value.map((u) => [u.id, u.name])))
const userOptions = computed(() => userList.value.map((u) => ({ value: u.id, label: u.name })))

function userLabel(entry) {
  if (entry.user_id) return userNames.value.get(entry.user_id) ?? `Usuário #${entry.user_id}`
  return entry.action === 'login_failed' ? 'Não autenticado' : 'Sistema'
}

// ---- Lista -------------------------------------------------------------------------------------------
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const updatedAt = ref(null)
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
    const res = await listAudit({
      entity: entidade.value || undefined,
      entity_id: entityId.value || undefined,
      action: acao.value || undefined,
      user_id: usuario.value || undefined,
      from: de.value || undefined,
      to: ate.value || undefined,
      page: page.value,
      per_page: PER_PAGE,
    })
    if (id !== requestId) return // resposta antiga
    rows.value = res.items
    total.value = res.total
    updatedAt.value = new Date()
    if (!res.items.length && res.total > 0 && page.value > 1) {
      router.replace({ query: { ...route.query, page: Math.ceil(res.total / PER_PAGE) } })
    }
  } catch (err) {
    if (id !== requestId) return
    error.value = err.message
    if (err.status === 403) toast.error('Somente administradores acessam a auditoria.')
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(
  () => route.query,
  () => {
    if (route.name === 'auditoria') load()
  },
)
onMounted(() => {
  users.load()
  load()
})

// ---- Tabela ----------------------------------------------------------------------------------------------
const columns = [
  { key: 'created_at', label: 'Data/hora' },
  { key: 'user_id', label: 'Usuário' },
  { key: 'action', label: 'Ação' },
  { key: 'entity', label: 'Entidade' },
  { key: 'entity_id', label: 'Id' },
  { key: 'ip', label: 'IP' },
  { key: 'actions', label: 'Detalhes' },
]

// Link para a tela da entidade (só quando faz sentido: registros excluídos não têm destino).
function entityLink(entry) {
  const name = AUDIT_ENTITY_ROUTES[entry.entity]
  if (!name || !entry.entity_id || entry.action === 'delete') return null
  if (entry.entity === 'product') {
    const productName = entry.after_json?.name ?? entry.before_json?.name
    return productName ? { name, query: { q: productName } } : { name }
  }
  return { name }
}

const detailOpen = ref(false)
const selected = ref(null)
function openDetail(entry) {
  selected.value = entry
  detailOpen.value = true
}
</script>

<template>
  <div class="space-y-5">
    <p class="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
      Trilha de auditoria: quem fez o quê, quando, de qual IP, com o antes e o depois. Os registros são imutáveis e nunca
      guardam senhas.
    </p>

    <div class="flex items-center justify-end gap-3">
      <span v-if="updatedAt" class="text-sm text-slate-500">Atualizado às {{ formatTime(updatedAt) }}</span>
      <BaseButton variant="secondary" size="sm" :loading="loading" @click="load">Atualizar</BaseButton>
    </div>

    <form class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-4" role="search" @submit.prevent>
      <BaseSelect label="Entidade" placeholder="Todas" :model-value="entidade" :options="entityOptions" @update:model-value="setQuery({ entidade: $event })" />
      <BaseInput label="Id da entidade" type="number" min="1" inputmode="numeric" :model-value="entityId" @update:model-value="setQuery({ id: $event })" />
      <BaseSelect label="Ação" placeholder="Todas" :model-value="acao" :options="actionOptions" @update:model-value="setQuery({ acao: $event })" />
      <BaseSelect label="Usuário" placeholder="Todos" :model-value="usuario" :options="userOptions" @update:model-value="setQuery({ usuario: $event })" />
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
      caption="Trilha de auditoria"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhum registro para os filtros' : 'Nenhum registro de auditoria'"
      :empty-description="hasFilters ? 'Ajuste ou limpe os filtros.' : ''"
    >
      <template #cell-created_at="{ value }"><span class="whitespace-nowrap">{{ formatDateTime(value) }}</span></template>
      <template #cell-user_id="{ row }">{{ userLabel(row) }}</template>
      <template #cell-action="{ value }">
        <BaseBadge :tone="AUDIT_ACTIONS[value]?.tone ?? 'slate'">{{ AUDIT_ACTIONS[value]?.label ?? value }}</BaseBadge>
      </template>
      <template #cell-entity="{ value }">{{ AUDIT_ENTITIES[value] ?? value }}</template>
      <template #cell-entity_id="{ row }">
        <template v-if="row.entity_id">
          <RouterLink v-if="entityLink(row)" :to="entityLink(row)" class="text-emerald-700 hover:underline">#{{ row.entity_id }}</RouterLink>
          <span v-else>#{{ row.entity_id }}</span>
        </template>
        <span v-else>—</span>
      </template>
      <template #cell-ip="{ value }">{{ value || '—' }}</template>
      <template #cell-actions="{ row }">
        <BaseButton variant="secondary" size="sm" :aria-label="`Ver mudanças do registro ${row.id}`" @click="openDetail(row)">Ver mudanças</BaseButton>
      </template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />

    <AuditDetailModal v-model="detailOpen" :entry="selected" :user-label="selected ? userLabel(selected) : ''" />
  </div>
</template>
