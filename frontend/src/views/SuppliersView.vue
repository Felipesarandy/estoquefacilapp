<script setup>
import { ref } from 'vue'
import { listSuppliers } from '../api/suppliers'
import SupplierFormModal from '../components/domain/SupplierFormModal.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import { useCrudList } from '../composables/useCrudList'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const list = useCrudList(listSuppliers, { routeName: 'fornecedores' })

const columns = [
  { key: 'name', label: 'Fornecedor' },
  { key: 'phone', label: 'Telefone' },
  { key: 'email', label: 'E-mail' },
  ...(auth.isAdmin ? [{ key: 'actions', label: 'Ações' }] : []),
]

const formOpen = ref(false)
const editing = ref(null)
function openForm(row = null) {
  editing.value = row
  formOpen.value = true
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Contatos de quem fornece os produtos.</p>
      <BaseButton v-if="auth.isAdmin" @click="openForm()">Novo fornecedor</BaseButton>
    </div>

    <form class="flex flex-wrap items-end gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" role="search" @submit.prevent>
      <div class="w-full sm:max-w-sm">
        <BaseInput v-model="list.search.value" label="Buscar" type="search" placeholder="Nome do fornecedor" />
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
      caption="Lista de fornecedores"
      :columns="columns"
      :rows="list.rows.value"
      :loading="list.loading.value"
      :empty-title="list.q.value ? 'Nenhum resultado para a busca' : 'Nenhum fornecedor cadastrado'"
      :empty-description="
        list.q.value
          ? 'Tente outro termo ou limpe a busca.'
          : auth.isAdmin
            ? 'Use “Novo fornecedor” para cadastrar o primeiro.'
            : 'O administrador ainda não cadastrou fornecedores.'
      "
    >
      <template #cell-name="{ row }"><span class="font-medium text-slate-800">{{ row.name }}</span></template>
      <template #cell-email="{ value }">
        <a v-if="value" :href="`mailto:${value}`" class="text-emerald-700 hover:underline">{{ value }}</a>
        <span v-else>—</span>
      </template>
      <template #cell-actions="{ row }">
        <BaseButton variant="secondary" size="sm" :aria-label="`Editar ${row.name}`" @click="openForm(row)">Editar</BaseButton>
      </template>
    </BaseTable>

    <BasePagination
      :page="list.page.value"
      :per-page="list.perPage"
      :total="list.total.value"
      @update:page="list.setPage"
    />

    <SupplierFormModal v-model="formOpen" :supplier="editing" @saved="list.load" />
  </div>
</template>
