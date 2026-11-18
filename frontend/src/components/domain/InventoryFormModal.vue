<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { createInventoryCount } from '../../api/inventory'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import { INCIDENT_SEVERITY, STOCK_LEVELS } from '../../utils/constants'
import { formatDecimal, formatQuantity } from '../../utils/format'
import { countDifference, differenceClass, signedDecimal } from '../../utils/inventory'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseTextarea from '../ui/BaseTextarea.vue'
import ConfirmDialog from '../ui/ConfirmDialog.vue'
import ProductSelect from './ProductSelect.vue'
import StockLevelBadge from './StockLevelBadge.vue'

const props = defineProps({
  modelValue: Boolean,
  products: { type: Array, default: () => [] }, // todos; só os ativos podem ser contados
})
const emit = defineEmits(['update:modelValue', 'saved', 'conflict'])

const toast = useToastStore()
const form = reactive({ product_id: '', counted_quantity: '', note: '' })
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const productSelect = ref(null)
const confirmOpen = ref(false)
const result = ref(null) // resposta real da API depois de salvar

const activeProducts = computed(() => props.products.filter((p) => p.active))
const product = computed(() => props.products.find((p) => String(p.id) === String(form.product_id)) ?? null)
const normalize = (v) => String(v).trim().replace(',', '.')
const countedValid = computed(() => /^\d+(\.\d{1,3})?$/.test(normalize(form.counted_quantity)))
const predicted = computed(() =>
  product.value && countedValid.value ? countDifference(normalize(form.counted_quantity), product.value.current_stock) : null,
)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    Object.assign(form, { product_id: '', counted_quantity: '', note: '' })
    result.value = null
    confirmOpen.value = false
    await nextTick()
    await nextTick()
    productSelect.value?.focus()
  },
)

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.product_id) errors.product_id = 'Selecione o produto.'
  const raw = normalize(form.counted_quantity)
  if (!raw) errors.counted_quantity = 'Informe a quantidade contada.'
  else if (!/^\d+(\.\d{1,3})?$/.test(raw)) errors.counted_quantity = 'Use um número maior ou igual a zero, com até 3 casas decimais.'
  if (form.note.length > 1000) errors.note = 'A observação deve ter até 1000 caracteres.'
  return Object.keys(errors).length === 0
}

// Divergência prevista exige confirmação explícita (a contagem é imutável).
function onSubmit() {
  if (submitting.value || !validate()) return
  if (predicted.value !== 0) confirmOpen.value = true
  else send()
}

async function send() {
  if (submitting.value) return
  confirmOpen.value = false
  const ok = await submit(async () => {
    try {
      result.value = await createInventoryCount({
        product_id: Number(form.product_id),
        counted_quantity: normalize(form.counted_quantity),
        note: form.note.trim() || null,
      })
    } catch (err) {
      if (err.status === 409) emit('conflict') // ex.: produto inativo; atualiza a lista de produtos
      else if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  if (ok) {
    toast.success('Contagem registrada.')
    emit('saved')
  }
}

const unit = computed(() => product.value?.unit ?? '')
const diffText = computed(() => {
  if (predicted.value === null) return ''
  if (predicted.value === 0) return 'Sem divergência'
  return `Será gerado um ajuste de ${signedDecimal(predicted.value)} ${unit.value} e um incidente de divergência.`
})
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="result ? 'Resultado da contagem' : 'Nova contagem'"
    size="lg"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- Resultado real devolvido pela API -->
    <div v-if="result" class="space-y-4" aria-live="polite">
      <dl class="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt class="text-xs font-medium uppercase text-slate-500">Saldo do sistema</dt><dd class="text-slate-800">{{ formatQuantity(result.count.system_quantity, unit) }}</dd></div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">Contado</dt><dd class="text-slate-800">{{ formatQuantity(result.count.counted_quantity, unit) }}</dd></div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Diferença</dt>
          <dd class="font-semibold" :class="differenceClass(result.difference)">{{ signedDecimal(result.difference) }} {{ unit }}</dd>
        </div>
      </dl>

      <p v-if="!result.adjustment" class="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-emerald-200">
        Sem divergência: nenhum ajuste necessário.
      </p>
      <div v-else class="space-y-2 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
        <p>
          Ajuste gerado: {{ result.adjustment.type === 'entrada' ? 'entrada' : 'saída' }} de
          {{ formatQuantity(result.adjustment.quantity, unit) }} (motivo: ajuste).
          <RouterLink :to="{ name: 'movimentacoes', query: { f_produto: result.count.product_id } }" class="font-medium underline">Ver movimentação</RouterLink>
        </p>
        <p v-if="result.incident">
          Incidente #{{ result.incident.id }} de divergência, gravidade
          {{ INCIDENT_SEVERITY[result.incident.severity]?.label ?? result.incident.severity }}.
          <RouterLink :to="{ name: 'incidentes', query: { status: 'todos', produto: result.count.product_id } }" class="font-medium underline">Ver incidentes</RouterLink>
        </p>
      </div>

      <p class="flex flex-wrap items-center gap-2 text-sm text-slate-700">
        Novo estoque: <strong>{{ formatQuantity(result.current_stock, unit) }}</strong>
        <StockLevelBadge :level="result.nivel" />
      </p>
    </div>

    <form v-else id="inventory-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">{{ formError }}</p>
      <p class="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 ring-1 ring-slate-200">
        A contagem é imutável: depois de registrada, não pode ser editada nem excluída.
      </p>

      <ProductSelect ref="productSelect" v-model="form.product_id" :products="activeProducts" required :error="errors.product_id" />

      <div v-if="product" class="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-slate-700 ring-1 ring-emerald-200" aria-live="polite">
        Saldo do sistema: <strong>{{ formatQuantity(product.current_stock, product.unit) }}</strong> · Colchão mínimo:
        <strong>{{ formatQuantity(product.min_stock, product.unit) }}</strong>
      </div>

      <BaseInput
        v-model="form.counted_quantity"
        label="Quantidade contada"
        inputmode="decimal"
        required
        :error="errors.counted_quantity"
        :help="product ? `Em ${product.unit}. Até 3 casas decimais; aceita vírgula.` : 'Até 3 casas decimais; aceita vírgula.'"
      />

      <p v-if="diffText" class="text-sm font-medium" :class="differenceClass(predicted)" aria-live="polite">
        Diferença prevista: {{ signedDecimal(predicted) }} {{ unit }}. {{ diffText }}
      </p>

      <BaseTextarea v-model="form.note" label="Observação" :error="errors.note" help="Opcional. Vai para a nota do ajuste, se houver divergência." />
    </form>

    <template #footer>
      <template v-if="result">
        <BaseButton @click="emit('update:modelValue', false)">Fechar</BaseButton>
      </template>
      <template v-else>
        <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
        <BaseButton type="submit" form="inventory-form" :loading="submitting">Registrar contagem</BaseButton>
      </template>
    </template>
  </BaseModal>

  <ConfirmDialog
    v-model="confirmOpen"
    title="Confirmar contagem com divergência?"
    :message="`${diffText} A contagem é imutável: não poderá ser editada nem excluída depois de registrada. O saldo usado será o do momento do envio.`"
    confirm-label="Registrar contagem"
    :loading="submitting"
    @confirm="send"
  />
</template>
