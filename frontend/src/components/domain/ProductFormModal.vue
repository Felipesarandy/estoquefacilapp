<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { createProduct, updateProduct } from '../../api/products'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import { UNITS, UNIT_LABELS } from '../../utils/constants'
import { formatDecimal } from '../../utils/format'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseSelect from '../ui/BaseSelect.vue'
import ErrorState from '../ui/ErrorState.vue'
import Spinner from '../ui/Spinner.vue'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null }, // null = criar
  categories: { type: Array, default: () => [] },
  suppliers: { type: Array, default: () => [] },
  refsLoading: Boolean,
  refsError: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'saved', 'retry-refs'])

const toast = useToastStore()
const isEdit = computed(() => !!props.product)

const form = reactive({
  name: '',
  code: '',
  category_id: '',
  supplier_id: '',
  unit: 'kg',
  cost_price: '0',
  min_stock: '0',
  max_stock: '',
  daily_consumption: '',
})
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const nameInput = ref(null)

const categoryOptions = computed(() => props.categories.map((c) => ({ value: c.id, label: c.name })))
const supplierOptions = computed(() => props.suppliers.map((s) => ({ value: s.id, label: s.name })))
const unitOptions = UNITS.map((u) => ({ value: u, label: UNIT_LABELS[u] }))

const toInput = (v) => (v === null || v === undefined ? '' : String(Number(v)))
const normalize = (v) => String(v).trim().replace(',', '.')

function fill() {
  const p = props.product
  form.name = p?.name ?? ''
  form.code = p?.code ?? ''
  form.category_id = p ? String(p.category_id) : ''
  form.supplier_id = p?.supplier_id ? String(p.supplier_id) : ''
  form.unit = p?.unit ?? 'kg'
  form.cost_price = p ? toInput(p.cost_price) : '0'
  form.min_stock = p ? toInput(p.min_stock) : '0'
  form.max_stock = p ? toInput(p.max_stock) : ''
  form.daily_consumption = p ? toInput(p.daily_consumption) : ''
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    fill()
    await nextTick()
    await nextTick()
    nameInput.value?.focus()
  },
)

// Campo decimal >= 0 com no máximo `scale` casas (mesmas regras da API).
function checkDecimal(field, scale, { required = false } = {}) {
  const raw = normalize(form[field])
  if (!raw) {
    if (required) errors[field] = 'Informe um valor.'
    return
  }
  if (!new RegExp(`^\\d+(\\.\\d{1,${scale}})?$`).test(raw)) {
    errors[field] = scale
      ? `Use um número maior ou igual a zero, com até ${scale} casas decimais.`
      : 'Use um número maior ou igual a zero.'
  }
}

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.name.trim()) errors.name = 'Informe o nome.'
  else if (form.name.trim().length > 150) errors.name = 'O nome deve ter até 150 caracteres.'
  if (form.code.trim().length > 50) errors.code = 'O código deve ter até 50 caracteres.'
  if (!form.category_id) errors.category_id = 'Selecione a categoria.'
  if (!form.unit) errors.unit = 'Selecione a unidade.'
  checkDecimal('cost_price', 2, { required: true })
  checkDecimal('min_stock', 3, { required: true })
  checkDecimal('max_stock', 3)
  checkDecimal('daily_consumption', 3)
  if (!errors.min_stock && !errors.max_stock && form.max_stock.trim()) {
    if (Number(normalize(form.max_stock)) < Number(normalize(form.min_stock))) {
      errors.max_stock = 'O máximo não pode ser menor que o mínimo.'
    }
  }
  return Object.keys(errors).length === 0
}

function buildPayload() {
  return {
    name: form.name.trim(),
    code: form.code.trim() || null,
    category_id: Number(form.category_id),
    supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
    unit: form.unit,
    cost_price: normalize(form.cost_price),
    min_stock: normalize(form.min_stock),
    max_stock: normalize(form.max_stock) || null,
    daily_consumption: normalize(form.daily_consumption) || null,
  }
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  const ok = await submit(async () => {
    try {
      const payload = buildPayload()
      if (isEdit.value) await updateProduct(props.product.id, payload)
      else await createProduct(payload)
    } catch (err) {
      // 409 = código já usado; 422 já traz o campo; rede/500 também vão para toast.
      if (err.status === 409) err.fields = { code: err.message }
      if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  if (ok) {
    toast.success(isEdit.value ? 'Produto atualizado.' : 'Produto cadastrado.')
    emit('update:modelValue', false)
    emit('saved')
  }
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="isEdit ? 'Editar produto' : 'Novo produto'"
    size="lg"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="refsLoading" class="flex justify-center py-8 text-emerald-600"><Spinner /></div>
    <ErrorState
      v-else-if="refsError"
      message="Não foi possível carregar categorias e fornecedores."
      @retry="emit('retry-refs')"
    />
    <form v-else id="product-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">
        {{ formError }}
      </p>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <BaseInput ref="nameInput" v-model="form.name" label="Nome" required :error="errors.name" />
        </div>
        <BaseInput v-model="form.code" label="Código" :error="errors.code" help="Opcional. Deve ser único." />
        <BaseSelect v-model="form.unit" label="Unidade" required :options="unitOptions" :error="errors.unit" />
        <BaseSelect
          v-model="form.category_id"
          label="Categoria"
          required
          placeholder="Selecione…"
          :options="categoryOptions"
          :error="errors.category_id"
        />
        <BaseSelect
          v-model="form.supplier_id"
          label="Fornecedor"
          placeholder="Sem fornecedor"
          :options="supplierOptions"
          :error="errors.supplier_id"
        />
        <BaseInput v-model="form.cost_price" label="Preço de custo (R$)" inputmode="decimal" required :error="errors.cost_price" />
        <BaseInput
          v-model="form.min_stock"
          label="Colchão mínimo"
          inputmode="decimal"
          required
          :error="errors.min_stock"
          help="Estoque de segurança."
        />
        <BaseInput v-model="form.max_stock" label="Estoque máximo" inputmode="decimal" :error="errors.max_stock" help="Opcional." />
        <BaseInput
          v-model="form.daily_consumption"
          label="Consumo diário"
          inputmode="decimal"
          :error="errors.daily_consumption"
          help="Opcional. Usado para calcular a cobertura em dias."
        />
      </div>

      <div v-if="isEdit" class="rounded-lg bg-slate-50 px-4 py-3 ring-1 ring-slate-200">
        <p class="text-sm font-medium text-slate-700">Estoque atual (somente leitura)</p>
        <p class="text-lg font-semibold text-slate-800">
          {{ formatDecimal(product.current_stock) }} {{ product.unit }}
        </p>
        <p class="text-sm text-slate-500">Altere o estoque em Movimentações.</p>
      </div>
      <p v-else class="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 ring-1 ring-slate-200">
        O produto começa com estoque zero. O estoque só é alterado por movimentações (entrada ou saída).
      </p>
    </form>

    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="product-form" :loading="submitting" :disabled="refsLoading || !!refsError">
        {{ isEdit ? 'Salvar alterações' : 'Cadastrar' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
