<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { deleteCategory, listCategories } from '../api/categories'
import CategoryFormModal from '../components/domain/CategoryFormModal.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useCrudList } from '../composables/useCrudList'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'

const auth = useAuthStore()
const toast = useToastStore()
const list = useCrudList(listCategories, { routeName: 'categorias' })

const columns = [
  { key: 'name', label: 'Categoria' },
  { key: 'products', label: 'Produtos' },
  ...(auth.isAdmin ? [{ key: 'actions', label: 'Ações' }] : []),
]

const formOpen = ref(false)
const editing = ref(null)
function openForm(row = null) {
  editing.value = row
  formOpen.value = true
}

// ---- Exclusão (só admin; a API recusa com 409 se houver produtos) -----------------
const confirmOpen = ref(false)
const target = ref(null)
const deleting = ref(false)
const blocked = ref(null) // { id, message } da última tentativa recusada

function askDelete(row) {
  target.value = row
  confirmOpen.value = true
}

async function confirmDelete() {
  if (deleting.value || !target.value) return
  const row = target.value
  deleting.value = true
  blocked.value = null
  try {
    await deleteCategory(row.id)
    toast.success('Categoria excluída.')
    confirmOpen.value = false
    await list.load() // se a página ficou vazia, useCrudList volta para a última página
  } catch (err) {
    confirmOpen.value = false
    if (err.status === 409) {
      blocked.value = { id: row.id, message: err.message }
      toast.error(err.message)
    } else if (err.status === 404) {
      toast.error(err.message)
      await list.load()
    } else {
      toast.error(err.status === 403 ? 'Você não tem permissão para excluir categorias.' : err.message)
    }
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Agrupe os produtos por categoria.</p>
      <BaseButton v-if="auth.isAdmin" @click="openForm()">Nova categoria</BaseButton>
    </div>

    <form class="flex flex-wrap items-end gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" role="search" @submit.prevent>
      <div class="w-full sm:max-w-sm">
        <BaseInput v-model="list.search.value" label="Buscar" type="search" placeholder="Nome da categoria" />
      </div>
      <BaseButton variant="secondary" size="sm" :disabled="!list.q.value && !list.search.value" @click="list.clearSearch">
        Limpar busca
      </BaseButton>
    </form>

    <div v-if="list.error.value && !list.loading.value" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="list.error.value" @retry="list.load" />
    </div>
    <BaseTable
      v-else
      caption="Lista de categorias"
      :columns="columns"
      :rows="list.rows.value"
      :loading="list.loading.value"
      :empty-title="list.q.value ? 'Nenhum resultado para a busca' : 'Nenhuma categoria cadastrada'"
      :empty-description="
        list.q.value
          ? 'Tente outro termo ou limpe a busca.'
          : auth.isAdmin
            ? 'Use “Nova categoria” para cadastrar a primeira.'
            : 'O administrador ainda não cadastrou categorias.'
      "
    >
      <template #cell-name="{ row }">
        <span class="font-medium text-slate-800">{{ row.name }}</span>
        <p v-if="blocked?.id === row.id" role="alert" class="mt-1 max-w-xs text-xs text-red-700">
          {{ blocked.message }}
          <RouterLink
            :to="{ name: 'produtos', query: { categoria: row.id } }"
            class="font-medium underline focus-visible:outline-2 focus-visible:outline-red-600"
          >
            Ver produtos desta categoria
          </RouterLink>
        </p>
      </template>
      <template #cell-products="{ row }">
        <RouterLink
          :to="{ name: 'produtos', query: { categoria: row.id } }"
          class="font-medium text-emerald-700 hover:underline focus-visible:outline-2 focus-visible:outline-emerald-600"
          :aria-label="`Ver produtos da categoria ${row.name}`"
        >
          Ver produtos
        </RouterLink>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex gap-2 whitespace-nowrap">
          <BaseButton variant="secondary" size="sm" :aria-label="`Editar ${row.name}`" @click="openForm(row)">Editar</BaseButton>
          <BaseButton variant="danger" size="sm" :aria-label="`Excluir ${row.name}`" @click="askDelete(row)">Excluir</BaseButton>
        </div>
      </template>
    </BaseTable>

    <BasePagination
      :page="list.page.value"
      :per-page="list.perPage"
      :total="list.total.value"
      @update:page="list.setPage"
    />

    <CategoryFormModal v-model="formOpen" :category="editing" @saved="list.load" />
    <ConfirmDialog
      v-model="confirmOpen"
      danger
      title="Excluir categoria?"
      :message="`Excluir categoria ${target?.name ?? ''}? Esta ação não pode ser desfeita.`"
      confirm-label="Excluir"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>
