<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listUsers, updateUser } from '../api/users'
import UserFormModal from '../components/domain/UserFormModal.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import { ROLES } from '../utils/constants'
import { formatDate } from '../utils/format'

const PER_PAGE = 10
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

// ---- Filtros na URL: ?q=&perfil=&situacao=&page= (situação padrão: ativos) -------------------------
const q = computed(() => String(route.query.q ?? ''))
const perfil = computed(() => (route.query.perfil in ROLES ? String(route.query.perfil) : ''))
const situacao = computed(() => (['inativos', 'todos'].includes(route.query.situacao) ? route.query.situacao : 'ativos'))
const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))
const hasFilters = computed(() => !!(q.value || perfil.value || situacao.value !== 'ativos'))

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
function clearFilters() {
  clearTimeout(debounceId)
  search.value = ''
  router.push({ query: {} })
}

const roleOptions = Object.entries(ROLES).map(([value, { label }]) => ({ value, label }))
const situationOptions = [
  { value: 'ativos', label: 'Ativos' },
  { value: 'inativos', label: 'Inativos' },
  { value: 'todos', label: 'Todos' },
]

// ---- Lista ----------------------------------------------------------------------------------------------
// A API filtra perfil e situação, mas não tem busca por texto: com busca, traz tudo e filtra/pagina aqui.
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let requestId = 0

async function fetchAll(params) {
  const all = []
  for (let p = 1; ; p++) {
    const res = await listUsers({ ...params, page: p, per_page: 100 })
    all.push(...res.items)
    if (!res.items.length || all.length >= res.total) return all
  }
}

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  const base = { role: perfil.value || undefined, active: situacao.value === 'todos' ? undefined : situacao.value === 'ativos' }
  try {
    let items
    let count
    if (q.value) {
      const term = q.value.toLowerCase()
      const filtered = (await fetchAll(base)).filter((u) => u.name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term))
      count = filtered.length
      items = filtered.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE)
    } else {
      const res = await listUsers({ ...base, page: page.value, per_page: PER_PAGE })
      items = res.items
      count = res.total
    }
    if (id !== requestId) return // resposta antiga
    rows.value = items
    total.value = count
    if (!items.length && count > 0 && page.value > 1) {
      setQuery({ page: Math.ceil(count / PER_PAGE) }, { replace: true, keepPage: true })
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
    if (route.name === 'usuarios') load()
  },
)
onMounted(load)

// ---- Tabela e ações -----------------------------------------------------------------------------------------
const columns = [
  { key: 'name', label: 'Nome' },
  { key: 'email', label: 'E-mail' },
  { key: 'role', label: 'Perfil' },
  { key: 'active', label: 'Situação' },
  { key: 'created_at', label: 'Criado em' },
  { key: 'actions', label: 'Ações' },
]
const isSelf = (row) => row.id === auth.user?.id

const formOpen = ref(false)
const editing = ref(null)
function openForm(row = null) {
  editing.value = row
  formOpen.value = true
}

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
    await updateUser(row.id, { active })
    toast.success(active ? 'Usuário reativado.' : 'Usuário desativado.')
    confirmOpen.value = false
    await load()
  } catch (err) {
    confirmOpen.value = false
    toast.error(err.status === 403 ? 'Você não tem permissão para alterar usuários.' : err.message)
  } finally {
    toggling.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <p class="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
      Gerencie quem acessa o sistema. Não há cadastro público; usuários são criados por um administrador. Usuários nunca
      são excluídos, apenas desativados.
    </p>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <BaseButton variant="secondary" size="sm" :loading="loading" @click="load">Atualizar</BaseButton>
      <BaseButton @click="openForm()">Novo usuário</BaseButton>
    </div>

    <form class="grid gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-4" role="search" @submit.prevent>
      <div class="lg:col-span-2">
        <BaseInput v-model="search" label="Buscar" type="search" placeholder="Nome ou e-mail" />
      </div>
      <BaseSelect label="Perfil" placeholder="Todos" :model-value="perfil" :options="roleOptions" @update:model-value="setQuery({ perfil: $event })" />
      <BaseSelect label="Situação" :model-value="situacao" :options="situationOptions" @update:model-value="setQuery({ situacao: $event })" />
      <div class="sm:col-span-2 lg:col-span-4">
        <BaseButton variant="secondary" size="sm" :disabled="!hasFilters && !search" @click="clearFilters">Limpar filtros</BaseButton>
      </div>
    </form>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <BaseTable
      v-else
      caption="Lista de usuários"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :empty-title="hasFilters ? 'Nenhum usuário para os filtros' : 'Nenhum usuário ativo'"
      :empty-description="hasFilters ? 'Ajuste ou limpe os filtros.' : ''"
    >
      <template #cell-name="{ row }">
        <span class="font-medium text-slate-800">{{ row.name }}</span>
        <span v-if="isSelf(row)" class="ml-1 text-xs text-slate-500">(você)</span>
      </template>
      <template #cell-role="{ value }">
        <BaseBadge :custom-class="ROLES[value]?.classes">{{ ROLES[value]?.label ?? value }}</BaseBadge>
      </template>
      <template #cell-active="{ value }">
        <BaseBadge :tone="value ? 'emerald' : 'slate'">{{ value ? 'Ativo' : 'Inativo' }}</BaseBadge>
      </template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ row }">
        <div class="flex gap-2 whitespace-nowrap">
          <BaseButton variant="secondary" size="sm" :aria-label="`Editar ${row.name}`" @click="openForm(row)">Editar</BaseButton>
          <BaseButton
            v-if="row.active"
            variant="danger"
            size="sm"
            :disabled="isSelf(row)"
            :title="isSelf(row) ? 'Você não pode desativar a própria conta.' : undefined"
            :aria-label="`Desativar ${row.name}`"
            @click="askDeactivate(row)"
          >
            Desativar
          </BaseButton>
          <BaseButton v-else size="sm" :disabled="toggling" :aria-label="`Reativar ${row.name}`" @click="setActive(row, true)">Reativar</BaseButton>
        </div>
      </template>
    </BaseTable>

    <BasePagination :page="page" :per-page="PER_PAGE" :total="total" @update:page="setQuery({ page: $event }, { keepPage: true })" />

    <UserFormModal v-model="formOpen" :user="editing" @saved="load" />
    <ConfirmDialog
      v-model="confirmOpen"
      danger
      title="Desativar usuário?"
      :message="`Ele não poderá mais entrar, mas o histórico é mantido.${target ? ` (${target.name})` : ''}`"
      confirm-label="Desativar"
      :loading="toggling"
      @confirm="setActive(target, false)"
    />
  </div>
</template>
