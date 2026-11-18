<script setup>
// Página de demonstração (somente em desenvolvimento): valida visualmente os componentes.
import { reactive, ref } from 'vue'
import StatCard from '../components/domain/StatCard.vue'
import StockLevelBadge from '../components/domain/StockLevelBadge.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import BaseModal from '../components/ui/BaseModal.vue'
import BasePagination from '../components/ui/BasePagination.vue'
import BaseSelect from '../components/ui/BaseSelect.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import BaseTextarea from '../components/ui/BaseTextarea.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Spinner from '../components/ui/Spinner.vue'
import { useApiForm } from '../composables/useApiForm'
import { usePagination } from '../composables/usePagination'
import { useToastStore } from '../stores/toast'
import { formatDateTime, formatDecimal, formatQuantity } from '../utils/format'

const toast = useToastStore()

const form = reactive({ nome: '', unidade: '', obs: '' })
const { errors, formError, submitting, submit, reset } = useApiForm(form)
async function simulate() {
  await submit(async () => {
    await new Promise((r) => setTimeout(r, 600))
    throw { fields: { nome: 'Nome já cadastrado (erro 422 simulado).' }, message: 'Dados inválidos' }
  })
}

const modalOpen = ref(false)
const confirmOpen = ref(false)

const columns = [
  { key: 'name', label: 'Produto' },
  { key: 'stock', label: 'Saldo' },
  { key: 'nivel', label: 'Nível' },
  { key: 'created_at', label: 'Criado em' },
]
const rows = [
  { id: 1, name: 'Ração extrusada', stock: formatQuantity('85.000', 'kg'), nivel: 'ok', created_at: '2026-11-17T22:27:25-03:00' },
  { id: 2, name: 'Feno de tifton', stock: formatQuantity('3.333', 'sc'), nivel: 'atencao', created_at: '2026-11-17T08:00:00-03:00' },
  { id: 3, name: 'Suplemento vitamínico', stock: formatQuantity('2.000', 'kg'), nivel: 'critico', created_at: '2026-11-16T10:15:00-03:00' },
  { id: 4, name: 'Aveia', stock: formatQuantity('0.000', 'kg'), nivel: 'ruptura', created_at: '2026-11-15T09:30:00-03:00' },
]
const pagination = usePagination(5)
pagination.total.value = 42

const tones = ['slate', 'emerald', 'amber', 'orange', 'red', 'sky', 'indigo']
</script>

<template>
  <div class="space-y-10">
    <section>
      <h2 class="mb-3 text-lg font-semibold text-slate-800">Botões e spinner</h2>
      <div class="flex flex-wrap items-center gap-3">
        <BaseButton>Primário</BaseButton>
        <BaseButton variant="secondary">Secundário</BaseButton>
        <BaseButton variant="danger">Perigo</BaseButton>
        <BaseButton size="sm">Pequeno</BaseButton>
        <BaseButton size="lg">Grande</BaseButton>
        <BaseButton loading>Salvando</BaseButton>
        <BaseButton disabled>Desabilitado</BaseButton>
        <span class="text-emerald-600"><Spinner /></span>
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-lg font-semibold text-slate-800">Badges e cartões</h2>
      <div class="flex flex-wrap gap-2">
        <BaseBadge v-for="t in tones" :key="t" :tone="t">{{ t }}</BaseBadge>
        <StockLevelBadge v-for="l in ['ruptura', 'critico', 'atencao', 'ok']" :key="l" :level="l" />
      </div>
      <div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Produtos ativos" value="38" />
        <StatCard title="Em alerta" value="4" detail="2 em ruptura" />
        <StatCard title="Saldo" :value="formatDecimal('85.000')" detail="kg de ração" />
        <StatCard title="Atualizado" :value="formatDateTime('2026-11-17T22:27:25-03:00')" />
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-lg font-semibold text-slate-800">Formulário (erro 422 simulado)</h2>
      <form class="max-w-md space-y-4" novalidate @submit.prevent="simulate">
        <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">{{ formError }}</p>
        <BaseInput v-model="form.nome" label="Nome" required help="Digite para limpar o erro." :error="errors.nome" />
        <BaseSelect
          v-model="form.unidade"
          label="Unidade"
          placeholder="Selecione…"
          :options="[{ value: 'kg', label: 'Quilo (kg)' }, { value: 'sc', label: 'Saco (sc)' }]"
          :error="errors.unidade"
        />
        <BaseTextarea v-model="form.obs" label="Observações" :error="errors.obs" />
        <div class="flex gap-2">
          <BaseButton type="submit" :loading="submitting">Enviar</BaseButton>
          <BaseButton variant="secondary" @click="reset">Limpar erros</BaseButton>
        </div>
      </form>
    </section>

    <section>
      <h2 class="mb-3 text-lg font-semibold text-slate-800">Toasts, modal e confirmação</h2>
      <div class="flex flex-wrap gap-3">
        <BaseButton variant="secondary" @click="toast.info('Mensagem informativa')">Info</BaseButton>
        <BaseButton variant="secondary" @click="toast.success('Salvo com sucesso')">Sucesso</BaseButton>
        <BaseButton variant="secondary" @click="toast.warning('Atenção ao estoque')">Aviso</BaseButton>
        <BaseButton variant="secondary" @click="toast.error('Algo deu errado')">Erro</BaseButton>
        <BaseButton @click="modalOpen = true">Abrir modal</BaseButton>
        <BaseButton variant="danger" @click="confirmOpen = true">Confirmar exclusão</BaseButton>
      </div>
      <BaseModal v-model="modalOpen" title="Modal de exemplo">
        <p class="mb-3 text-sm text-slate-600">Esc, clique fora ou o X fecham. O foco volta ao botão.</p>
        <BaseInput label="Campo dentro do modal" />
        <template #footer>
          <BaseButton variant="secondary" @click="modalOpen = false">Fechar</BaseButton>
          <BaseButton @click="modalOpen = false">Salvar</BaseButton>
        </template>
      </BaseModal>
      <ConfirmDialog
        v-model="confirmOpen"
        danger
        title="Desativar produto?"
        message="Essa ação pode ser desfeita reativando o cadastro."
        confirm-label="Desativar"
        @confirm="confirmOpen = false; toast.success('Produto desativado')"
      />
    </section>

    <section>
      <h2 class="mb-3 text-lg font-semibold text-slate-800">Tabela e paginação</h2>
      <BaseTable caption="Produtos de exemplo" :columns="columns" :rows="rows">
        <template #cell-nivel="{ row }"><StockLevelBadge :level="row.nivel" /></template>
        <template #cell-created_at="{ value }">{{ formatDateTime(value) }}</template>
      </BaseTable>
      <div class="mt-4">
        <BasePagination
          :page="pagination.page.value"
          :per-page="pagination.perPage.value"
          :total="pagination.total.value"
          @update:page="pagination.setPage"
        />
      </div>
      <h3 class="mb-2 mt-6 font-medium text-slate-700">Tabela vazia / carregando</h3>
      <div class="grid gap-4 lg:grid-cols-2">
        <BaseTable :columns="columns" :rows="[]" empty-description="Tente ajustar os filtros." />
        <BaseTable :columns="columns" :rows="[]" loading />
      </div>
      <EmptyState class="mt-4" title="Sem alertas" description="Tudo certo com o estoque." />
    </section>
  </div>
</template>
