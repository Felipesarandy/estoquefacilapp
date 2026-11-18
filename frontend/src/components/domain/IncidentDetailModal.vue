<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { listAudit } from '../../api/audit'
import { getIncident, updateIncident } from '../../api/incidents'
import { useApiForm } from '../../composables/useApiForm'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import { INCIDENT_SEVERITY, INCIDENT_STATUS, INCIDENT_TRANSITIONS, INCIDENT_TYPES } from '../../utils/constants'
import { formatDateTime } from '../../utils/format'
import BaseBadge from '../ui/BaseBadge.vue'
import BaseButton from '../ui/BaseButton.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseTextarea from '../ui/BaseTextarea.vue'
import ErrorState from '../ui/ErrorState.vue'
import Spinner from '../ui/Spinner.vue'
import StockLevelBadge from './StockLevelBadge.vue'

const props = defineProps({
  modelValue: Boolean,
  incidentId: { type: Number, default: null },
  products: { type: Map, default: () => new Map() }, // id -> produto (com nivel)
  userNames: { type: Map, default: () => new Map() },
})
const emit = defineEmits(['update:modelValue', 'changed'])

const auth = useAuthStore()
const toast = useToastStore()

const incident = ref(null)
const loading = ref(false)
const loadError = ref('')
const history = ref([]) // registros de auditoria (só admin)

const form = ref({ resolution: '' })
const { errors, formError, submitting, reset, submit } = useApiForm()
const pending = ref(null) // transição aguardando o texto de resolução

const product = computed(() => props.products.get(incident.value?.product_id) ?? null)
const transitions = computed(() => (auth.isAdmin && incident.value ? INCIDENT_TRANSITIONS[incident.value.status] ?? [] : []))
const userName = (id) => (id ? props.userNames.get(id) ?? (id === auth.user?.id ? auth.user.name : `Usuário #${id}`) : '—')

async function load() {
  loading.value = true
  loadError.value = ''
  history.value = []
  try {
    incident.value = await getIncident(props.incidentId)
    if (auth.isAdmin) {
      // Histórico de status vem da trilha de auditoria (admin); se falhar, usa só as datas do incidente.
      try {
        const res = await listAudit({ entity: 'incident', entity_id: props.incidentId, per_page: 100 })
        history.value = res.items.slice().reverse()
      } catch {
        history.value = []
      }
    }
  } catch (err) {
    loadError.value = err.message
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    incident.value = null
    pending.value = null
    reset()
    load()
  },
)

// Linha do tempo: mudanças de status da auditoria ou, sem ela, as datas do próprio incidente.
const timeline = computed(() => {
  const events = []
  for (const log of history.value) {
    const before = log.before_json?.status
    const after = log.after_json?.status
    if (!log.before_json) events.push({ at: log.created_at, text: `Aberto (${INCIDENT_STATUS[after]?.label ?? after})`, who: log.user_id })
    else if (before !== after) {
      events.push({
        at: log.created_at,
        text: `${INCIDENT_STATUS[before]?.label ?? before} → ${INCIDENT_STATUS[after]?.label ?? after}`,
        who: log.user_id,
      })
    }
  }
  if (events.length) return events
  const i = incident.value
  if (!i) return []
  const fallback = [{ at: i.opened_at, text: 'Incidente aberto', who: i.opened_by_id }]
  if (i.closed_at) fallback.push({ at: i.closed_at, text: 'Atendimento encerrado (resolvido)', who: null })
  return fallback
})

function chooseTransition(t) {
  reset()
  if (t.needsText) {
    pending.value = t
    form.value.resolution = incident.value.resolution ?? ''
  } else {
    apply(t)
  }
}

async function apply(t) {
  if (submitting.value) return
  if (t.needsText && !form.value.resolution.trim()) {
    errors.resolution = 'Informe a resolução.'
    return
  }
  const ok = await submit(async () => {
    try {
      const payload = { status: t.to }
      if (t.needsText) payload.resolution = form.value.resolution.trim()
      incident.value = await updateIncident(incident.value.id, payload)
    } catch (err) {
      if (err.status === 403) toast.error('Você não tem permissão para alterar incidentes.')
      else if (err.status === 0 || err.status >= 500) toast.error(err.message)
      if (err.status === 409) {
        // Status desatualizado ou transição inválida: mostra o motivo e recarrega o incidente.
        toast.error(err.message)
        pending.value = null
        load()
        emit('changed')
      }
      throw err
    }
  })
  if (ok) {
    toast.success(`Incidente atualizado: ${INCIDENT_STATUS[t.to].label}.`)
    pending.value = null
    emit('changed')
    load() // atualiza também a linha do tempo
  }
}

const field = 'text-sm text-slate-700'
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="incident ? `Incidente #${incident.id}` : 'Incidente'"
    size="lg"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="loading && !incident" class="flex justify-center py-10 text-emerald-600"><Spinner /></div>
    <ErrorState v-else-if="loadError" :message="loadError" @retry="load" />
    <div v-else-if="incident" class="space-y-5">
      <div class="flex flex-wrap items-center gap-2">
        <span class="font-semibold text-slate-800">{{ INCIDENT_TYPES[incident.type] ?? incident.type }}</span>
        <BaseBadge :custom-class="INCIDENT_SEVERITY[incident.severity]?.classes">{{ INCIDENT_SEVERITY[incident.severity]?.label ?? incident.severity }}</BaseBadge>
        <BaseBadge :custom-class="INCIDENT_STATUS[incident.status]?.classes">{{ INCIDENT_STATUS[incident.status]?.label ?? incident.status }}</BaseBadge>
      </div>

      <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Produto</dt>
          <dd :class="field">
            <template v-if="incident.product_id">
              <RouterLink
                v-if="product"
                :to="{ name: 'produtos', query: { q: product.name } }"
                class="font-medium text-emerald-700 hover:underline"
              >
                {{ product.name }}
              </RouterLink>
              <span v-else>Produto #{{ incident.product_id }}</span>
              <StockLevelBadge v-if="product" class="ml-2" :level="product.nivel" />
            </template>
            <span v-else>Sem produto</span>
          </dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Responsável</dt>
          <dd :class="field">{{ userName(incident.assigned_to_id) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Aberto em</dt>
          <dd :class="field">{{ formatDateTime(incident.opened_at) }} por {{ userName(incident.opened_by_id) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase text-slate-500">Atendimento encerrado em</dt>
          <dd :class="field">{{ incident.closed_at ? formatDateTime(incident.closed_at) : '—' }}</dd>
        </div>
        <div class="sm:col-span-2">
          <dt class="text-xs font-medium uppercase text-slate-500">Descrição</dt>
          <dd :class="[field, 'whitespace-pre-line']">{{ incident.description }}</dd>
        </div>
        <div class="sm:col-span-2">
          <dt class="text-xs font-medium uppercase text-slate-500">Resolução</dt>
          <dd :class="[field, 'whitespace-pre-line']">{{ incident.resolution || '—' }}</dd>
        </div>
      </dl>

      <section aria-labelledby="titulo-linha-tempo">
        <h3 id="titulo-linha-tempo" class="mb-2 text-sm font-semibold text-slate-800">Linha do tempo</h3>
        <ol class="space-y-2 border-l-2 border-slate-200 pl-4">
          <li v-for="(e, i) in timeline" :key="i" class="text-sm">
            <span class="font-medium text-slate-800">{{ e.text }}</span>
            <span class="block text-xs text-slate-500">
              {{ formatDateTime(e.at) }}<template v-if="e.who"> · {{ userName(e.who) }}</template>
            </span>
          </li>
        </ol>
        <RouterLink
          v-if="auth.isAdmin"
          :to="{ name: 'auditoria', query: { entidade: 'incident', id: incident.id } }"
          class="mt-2 inline-block text-sm font-medium text-emerald-700 hover:underline focus-visible:outline-2 focus-visible:outline-emerald-600"
          @click="emit('update:modelValue', false)"
        >
          Ver na auditoria
        </RouterLink>
      </section>

      <section v-if="auth.isAdmin" aria-labelledby="titulo-acoes">
        <h3 id="titulo-acoes" class="mb-2 text-sm font-semibold text-slate-800">Ações</h3>
        <p v-if="formError" role="alert" class="mb-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">{{ formError }}</p>
        <p v-if="!transitions.length" class="text-sm text-slate-500">Incidente fechado: não há mais transições.</p>

        <form v-if="pending" novalidate class="space-y-3" @submit.prevent="apply(pending)">
          <BaseTextarea v-model="form.resolution" label="Resolução" required :rows="4" :error="errors.resolution" help="Descreva como o incidente foi resolvido." />
          <div class="flex gap-2">
            <BaseButton type="submit" :loading="submitting">Confirmar: {{ pending.label }}</BaseButton>
            <BaseButton variant="secondary" :disabled="submitting" @click="pending = null">Cancelar</BaseButton>
          </div>
        </form>
        <div v-else class="flex flex-wrap gap-2">
          <BaseButton
            v-for="t in transitions"
            :key="t.to"
            :variant="t.to === 'fechado' || t.to === 'resolvido' ? 'primary' : 'secondary'"
            :loading="submitting"
            @click="chooseTransition(t)"
          >
            {{ t.label }}
          </BaseButton>
        </div>
      </section>
      <p v-else class="text-sm text-slate-500">Somente o administrador pode alterar o status do incidente.</p>
    </div>
  </BaseModal>
</template>
