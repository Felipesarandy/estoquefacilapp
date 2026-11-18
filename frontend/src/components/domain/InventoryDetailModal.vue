<script setup>
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { listAudit } from '../../api/audit'
import { useAuthStore } from '../../stores/auth'
import { formatDateTime, formatQuantity } from '../../utils/format'
import { differenceClass, signedDecimal } from '../../utils/inventory'
import BaseBadge from '../ui/BaseBadge.vue'
import BaseModal from '../ui/BaseModal.vue'

const props = defineProps({
  modelValue: Boolean,
  count: { type: Object, default: null },
  product: { type: Object, default: null },
  userLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const auth = useAuthStore()

// Só o admin lê a auditoria: de lá vêm a observação e os ids do ajuste e do incidente gerados.
const extra = ref(null)
watch(
  () => props.modelValue,
  async (open) => {
    extra.value = null
    if (!open || !props.count || !auth.isAdmin) return
    try {
      const res = await listAudit({ entity: 'inventory_count', entity_id: props.count.id, per_page: 1 })
      extra.value = res.items[0]?.after_json ?? null
    } catch {
      extra.value = null
    }
  },
)
</script>

<template>
  <BaseModal :model-value="modelValue" :title="count ? `Contagem #${count.id}` : 'Contagem'" @update:model-value="emit('update:modelValue', $event)">
    <div v-if="count" class="space-y-4 text-sm">
      <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Produto</dt>
          <dd>
            <RouterLink v-if="product" :to="{ name: 'produtos', query: { q: product.name } }" class="font-medium text-emerald-700 hover:underline" @click="emit('update:modelValue', false)">
              {{ product.name }}
            </RouterLink>
            <span v-else>Produto #{{ count.product_id }}</span>
          </dd>
        </div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">Quando</dt><dd>{{ formatDateTime(count.created_at) }}</dd></div>
        <div v-if="userLabel"><dt class="text-xs font-medium uppercase text-slate-500">Usuário</dt><dd>{{ userLabel }}</dd></div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Resultado</dt>
          <dd><BaseBadge :tone="Number(count.difference) === 0 ? 'emerald' : 'orange'">{{ Number(count.difference) === 0 ? 'Sem divergência' : 'Divergência' }}</BaseBadge></dd>
        </div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">Saldo do sistema</dt><dd>{{ formatQuantity(count.system_quantity, product?.unit) }}</dd></div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">Quantidade contada</dt><dd>{{ formatQuantity(count.counted_quantity, product?.unit) }}</dd></div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Diferença</dt>
          <dd class="font-semibold" :class="differenceClass(count.difference)">{{ signedDecimal(count.difference) }} {{ product?.unit }}</dd>
        </div>
        <div v-if="extra?.note" class="sm:col-span-2">
          <dt class="text-xs font-medium uppercase text-slate-500">Observação</dt>
          <dd class="whitespace-pre-line">{{ extra.note }}</dd>
        </div>
      </dl>

      <ul class="flex flex-wrap gap-x-5 gap-y-2">
        <li v-if="extra?.adjustment_id">
          <RouterLink :to="{ name: 'movimentacoes', query: { f_produto: count.product_id } }" class="font-medium text-emerald-700 hover:underline" @click="emit('update:modelValue', false)">
            Ver movimentação de ajuste #{{ extra.adjustment_id }}
          </RouterLink>
        </li>
        <li v-if="extra?.incident_id">
          <RouterLink :to="{ name: 'incidentes', query: { status: 'todos', produto: count.product_id } }" class="font-medium text-emerald-700 hover:underline" @click="emit('update:modelValue', false)">
            Ver incidente #{{ extra.incident_id }}
          </RouterLink>
        </li>
        <li v-if="auth.isAdmin">
          <RouterLink :to="{ name: 'auditoria', query: { entidade: 'inventory_count', id: count.id } }" class="font-medium text-emerald-700 hover:underline" @click="emit('update:modelValue', false)">
            Ver na auditoria
          </RouterLink>
        </li>
      </ul>
      <p class="text-xs text-slate-500">Contagens são imutáveis: não podem ser editadas nem excluídas.</p>
    </div>
  </BaseModal>
</template>
