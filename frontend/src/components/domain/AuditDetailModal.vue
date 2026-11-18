<script setup>
import { computed, ref, watch } from 'vue'
import { useToastStore } from '../../stores/toast'
import { AUDIT_ACTIONS, AUDIT_ENTITIES, AUDIT_FIELDS } from '../../utils/constants'
import { diffSnapshots, formatAuditValue, maskSensitive } from '../../utils/audit'
import { formatDateTime } from '../../utils/format'
import BaseBadge from '../ui/BaseBadge.vue'
import BaseButton from '../ui/BaseButton.vue'
import BaseModal from '../ui/BaseModal.vue'

const props = defineProps({
  modelValue: Boolean,
  entry: { type: Object, default: null },
  userLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const toast = useToastStore()

const showUnchanged = ref(false)
const showJson = ref(false)
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      showUnchanged.value = false
      showJson.value = false
    }
  },
)

const rows = computed(() => (props.entry ? diffSnapshots(props.entry.before_json, props.entry.after_json) : []))
const hasBothSides = computed(() => !!props.entry?.before_json && !!props.entry?.after_json)
const visibleRows = computed(() =>
  hasBothSides.value && !showUnchanged.value ? rows.value.filter((r) => r.change !== 'same') : rows.value,
)
const hiddenCount = computed(() => rows.value.length - visibleRows.value.length)
const json = computed(() =>
  JSON.stringify({ before: maskSensitive(props.entry?.before_json ?? null), after: maskSensitive(props.entry?.after_json ?? null) }, null, 2),
)

async function copy() {
  try {
    await navigator.clipboard.writeText(json.value)
    toast.success('JSON copiado.')
  } catch {
    toast.error('Não foi possível copiar. Selecione o texto e copie manualmente.')
  }
}

const label = (key) => AUDIT_FIELDS[key] ?? key
const action = computed(() => AUDIT_ACTIONS[props.entry?.action] ?? { label: props.entry?.action, tone: 'slate' })
</script>

<template>
  <BaseModal :model-value="modelValue" :title="entry ? `Registro #${entry.id}` : 'Registro'" size="lg" @update:model-value="emit('update:modelValue', $event)">
    <div v-if="entry" class="space-y-5">
      <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        <div><dt class="text-xs font-medium uppercase text-slate-500">Quem</dt><dd class="text-slate-800">{{ userLabel }}</dd></div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">Quando</dt><dd class="text-slate-800">{{ formatDateTime(entry.created_at) }}</dd></div>
        <div><dt class="text-xs font-medium uppercase text-slate-500">IP</dt><dd class="text-slate-800">{{ entry.ip || '—' }}</dd></div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Ação</dt>
          <dd><BaseBadge :tone="action.tone">{{ action.label }}</BaseBadge></dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Entidade</dt>
          <dd class="text-slate-800">{{ AUDIT_ENTITIES[entry.entity] ?? entry.entity }}<template v-if="entry.entity_id"> #{{ entry.entity_id }}</template></dd>
        </div>
      </dl>

      <section aria-labelledby="titulo-mudancas">
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 id="titulo-mudancas" class="text-sm font-semibold text-slate-800">Antes × Depois</h3>
          <label v-if="hasBothSides && rows.length" class="inline-flex items-center gap-2 text-sm text-slate-600">
            <input v-model="showUnchanged" type="checkbox" class="size-4 rounded border-slate-300 text-emerald-600" />
            Mostrar campos sem alteração
          </label>
        </div>

        <p v-if="!rows.length" class="text-sm text-slate-500">Este registro não guarda valores antes/depois.</p>
        <template v-else>
          <div class="hidden gap-3 px-3 pb-1 text-xs font-semibold uppercase text-slate-500 sm:grid sm:grid-cols-[10rem_1fr_1fr]">
            <span>Campo</span><span>Antes</span><span>Depois</span>
          </div>
          <ul class="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
            <li
              v-for="r in visibleRows"
              :key="r.key"
              class="grid gap-1 px-3 py-2 text-sm sm:grid-cols-[10rem_1fr_1fr] sm:gap-3"
              :class="r.change === 'same' ? 'text-slate-500' : 'bg-white'"
            >
              <span class="font-medium text-slate-700">
                {{ label(r.key) }}
                <span v-if="r.change === 'added'" class="ml-1 text-xs font-normal text-emerald-700">(novo)</span>
                <span v-else-if="r.change === 'removed'" class="ml-1 text-xs font-normal text-rose-700">(removido)</span>
              </span>
              <span
                class="break-words"
                :class="r.change === 'changed' || r.change === 'removed' ? 'text-rose-700/70 line-through' : ''"
              >
                <span class="text-xs text-slate-400 sm:hidden">Antes: </span>{{ r.hasBefore ? formatAuditValue(r.before) : '—' }}
              </span>
              <span class="break-words" :class="r.change === 'changed' || r.change === 'added' ? 'font-medium text-emerald-700' : ''">
                <span class="text-xs text-slate-400 sm:hidden">Depois: </span>{{ r.hasAfter ? formatAuditValue(r.after) : '—' }}
              </span>
            </li>
          </ul>
          <p v-if="hiddenCount" class="mt-2 text-xs text-slate-500">{{ hiddenCount }} campo(s) sem alteração oculto(s).</p>
        </template>
      </section>

      <section>
        <BaseButton variant="secondary" size="sm" :aria-expanded="showJson" aria-controls="audit-json" @click="showJson = !showJson">
          {{ showJson ? 'Ocultar JSON completo' : 'Mostrar JSON completo' }}
        </BaseButton>
        <div v-if="showJson" id="audit-json" class="mt-3">
          <div class="mb-1 flex justify-end"><BaseButton variant="secondary" size="sm" @click="copy">Copiar</BaseButton></div>
          <pre class="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100" tabindex="0">{{ json }}</pre>
        </div>
      </section>
    </div>
  </BaseModal>
</template>
