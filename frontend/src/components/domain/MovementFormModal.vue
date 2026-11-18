<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { createMovement } from '../../api/movements'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import { ENTRY_REASONS, EXIT_REASONS, MOVEMENT_REASONS, MOVEMENT_TYPES, STOCK_LEVELS } from '../../utils/constants'
import { formatDecimal, formatQuantity } from '../../utils/format'
import { predictLevel } from '../../utils/stock'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseSelect from '../ui/BaseSelect.vue'
import BaseTextarea from '../ui/BaseTextarea.vue'
import ProductSelect from './ProductSelect.vue'
import StockLevelBadge from './StockLevelBadge.vue'

const props = defineProps({
  modelValue: Boolean,
  products: { type: Array, default: () => [] }, // todos; aqui só os ativos podem ser movimentados
  initialProduct: { type: [String, Number], default: '' },
  initialType: { type: String, default: 'entrada' },
  daysAhead: { type: Number, default: 5 },
})
const emit = defineEmits(['update:modelValue', 'saved', 'conflict'])

const toast = useToastStore()
const form = reactive({
  product_id: '',
  type: 'entrada',
  reason: '',
  quantity: '',
  batch: '',
  expiration_date: '',
  note: '',
})
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const productSelect = ref(null)

const activeProducts = computed(() => props.products.filter((p) => p.active))
const product = computed(() => props.products.find((p) => String(p.id) === String(form.product_id)) ?? null)
const typeOptions = Object.entries(MOVEMENT_TYPES).map(([value, label]) => ({ value, label }))
const reasonOptions = computed(() =>
  (form.type === 'entrada' ? ENTRY_REASONS : EXIT_REASONS).map((r) => ({ value: r, label: MOVEMENT_REASONS[r] })),
)

// Troca de tipo: mantém o motivo só se ele existir no novo tipo.
watch(
  () => form.type,
  () => {
    if (!reasonOptions.value.some((o) => o.value === form.reason)) form.reason = ''
    if (form.type === 'saida') {
      form.batch = ''
      form.expiration_date = ''
    }
  },
)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    Object.assign(form, {
      product_id: props.initialProduct ? String(props.initialProduct) : '',
      type: props.initialType === 'saida' ? 'saida' : 'entrada',
      reason: '',
      quantity: '',
      batch: '',
      expiration_date: '',
      note: '',
    })
    await nextTick()
    await nextTick()
    productSelect.value?.focus()
  },
)

const normalize = (v) => String(v).trim().replace(',', '.')
const quantityValid = computed(() => /^\d+(\.\d{1,3})?$/.test(normalize(form.quantity)) && Number(normalize(form.quantity)) > 0)
const quantity = computed(() => (quantityValid.value ? Number(normalize(form.quantity)) : null))

const stockAfter = computed(() => {
  if (!product.value || quantity.value === null) return null
  const sign = form.type === 'entrada' ? 1 : -1
  return Number(product.value.current_stock) + sign * quantity.value
})
const predictedLevel = computed(() =>
  stockAfter.value === null
    ? null
    : predictLevel(stockAfter.value, product.value.min_stock, product.value.daily_consumption, props.daysAhead),
)
const exceedsStock = computed(() => form.type === 'saida' && stockAfter.value !== null && stockAfter.value < 0)

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.product_id) errors.product_id = 'Selecione o produto.'
  if (!form.reason) errors.reason = 'Selecione o motivo.'
  const raw = normalize(form.quantity)
  if (!raw) errors.quantity = 'Informe a quantidade.'
  else if (!/^\d+(\.\d{1,3})?$/.test(raw)) errors.quantity = 'Use um número com até 3 casas decimais.'
  else if (Number(raw) <= 0) errors.quantity = 'A quantidade deve ser maior que zero.'
  if (form.batch.trim().length > 50) errors.batch = 'O lote deve ter até 50 caracteres.'
  if (form.expiration_date && !/^\d{4}-\d{2}-\d{2}$/.test(form.expiration_date)) {
    errors.expiration_date = 'Informe uma data válida.'
  }
  if (form.note.length > 5000) errors.note = 'A observação deve ter até 5000 caracteres.'
  return Object.keys(errors).length === 0
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  let result = null
  const selected = product.value
  const ok = await submit(async () => {
    try {
      result = await createMovement({
        product_id: Number(form.product_id),
        type: form.type,
        reason: form.reason,
        quantity: normalize(form.quantity),
        batch: form.batch.trim() || null,
        expiration_date: form.expiration_date || null,
        note: form.note.trim() || null,
      })
    } catch (err) {
      if (err.status === 409) {
        // Mantém o modal e os campos; informa o disponível e pede ao pai para atualizar os saldos.
        if (selected && /estoque insuficiente/i.test(err.message)) {
          err.message = `${err.message}. Disponível: ${formatQuantity(selected.current_stock, selected.unit)}.`
        }
        emit('conflict')
      } else if (err.status === 0 || err.status >= 500 || err.status === 403) {
        toast.error(err.message)
      }
      throw err
    }
  })
  if (!ok) return

  const nivelNovo = result.nivel
  let message = `Movimentação registrada. Novo estoque: ${formatQuantity(result.current_stock, selected?.unit)} (${STOCK_LEVELS[nivelNovo]?.label ?? nivelNovo}).`
  if (nivelNovo === 'ruptura') message += ' Um incidente de ruptura foi aberto.'
  else if (selected?.nivel === 'ruptura' && form.type === 'entrada') message += ' O incidente de ruptura foi resolvido.'
  toast.success(message)
  emit('update:modelValue', false)
  emit('saved', result)
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="form.type === 'entrada' ? 'Registrar entrada' : 'Registrar saída'"
    size="lg"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form id="movement-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">
        {{ formError }}
      </p>
      <p class="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 ring-1 ring-slate-200">
        Movimentações não podem ser editadas nem excluídas. Para corrigir um lançamento, registre uma movimentação de
        ajuste.
      </p>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <ProductSelect
            ref="productSelect"
            v-model="form.product_id"
            :products="activeProducts"
            required
            :error="errors.product_id"
          />
        </div>

        <div
          v-if="product"
          class="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-slate-700 ring-1 ring-emerald-200 sm:col-span-2"
          aria-live="polite"
        >
          <p>
            Estoque atual: <strong>{{ formatQuantity(product.current_stock, product.unit) }}</strong> · Colchão mínimo:
            <strong>{{ formatQuantity(product.min_stock, product.unit) }}</strong>
          </p>
          <p v-if="stockAfter !== null" class="mt-1 flex flex-wrap items-center gap-2">
            Estoque após a movimentação:
            <strong>{{ formatQuantity(formatDecimal(stockAfter), product.unit) }}</strong>
            <StockLevelBadge :level="predictedLevel" />
          </p>
          <p v-if="exceedsStock" class="mt-1 font-medium text-amber-700">
            A quantidade é maior que o estoque disponível. A API vai recusar a saída.
          </p>
        </div>

        <BaseSelect v-model="form.type" label="Tipo" required :options="typeOptions" :error="errors.type" />
        <BaseSelect
          v-model="form.reason"
          label="Motivo"
          required
          placeholder="Selecione…"
          :options="reasonOptions"
          :error="errors.reason"
        />
        <BaseInput
          v-model="form.quantity"
          label="Quantidade"
          inputmode="decimal"
          required
          :error="errors.quantity"
          :help="product ? `Em ${product.unit}. Até 3 casas decimais.` : 'Até 3 casas decimais.'"
        />
        <template v-if="form.type === 'entrada'">
          <BaseInput v-model="form.batch" label="Lote" :error="errors.batch" help="Opcional." />
          <BaseInput v-model="form.expiration_date" label="Validade" type="date" :error="errors.expiration_date" help="Opcional." />
        </template>
        <div class="sm:col-span-2">
          <BaseTextarea v-model="form.note" label="Observação" :error="errors.note" />
        </div>
      </div>
      <p v-if="product" class="text-xs text-slate-500">
        O custo unitário é o preço de custo do produto ({{ product.cost_price }}), aplicado automaticamente pela API.
      </p>
    </form>

    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="movement-form" :loading="submitting">Registrar</BaseButton>
    </template>
  </BaseModal>
</template>
