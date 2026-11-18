<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDashboard } from '../api/dashboard'
import { getDailyMovements, listAllMovements } from '../api/movements'
import { listAllProducts } from '../api/products'
import MovementFormModal from '../components/domain/MovementFormModal.vue'
import MovementsChart from '../components/domain/MovementsChart.vue'
import StatCard from '../components/domain/StatCard.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import Spinner from '../components/ui/Spinner.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { MOVEMENT_REASONS, MOVEMENT_TYPES } from '../utils/constants'
import { csvNumber, downloadCsv } from '../utils/csv'
import {
  addDays,
  daysBetween,
  formatDate,
  formatDateWeekday,
  formatDecimal,
  formatQuantity,
  formatTime,
  todayISO,
} from '../utils/format'

const PRESETS = [7, 15, 30]
const MAX_DAYS = 31 // limite da API para from/to
const route = useRoute()
const router = useRouter()

// ---- Período (URL: ?dias= ou ?de=&ate=) ----------------------------------------------------
const isCustom = computed(() => route.query.de !== undefined || route.query.ate !== undefined)
const presetDays = computed(() => (PRESETS.includes(Number(route.query.dias)) ? Number(route.query.dias) : 7))
const de = computed(() => String(route.query.de ?? ''))
const ate = computed(() => String(route.query.ate ?? ''))

const rangeError = computed(() => {
  if (!isCustom.value) return ''
  if (!de.value || !ate.value) return 'Informe a data inicial e a final.'
  if (de.value > ate.value) return 'A data final deve ser igual ou posterior à inicial.'
  if (daysBetween(de.value, ate.value) > MAX_DAYS) return `O período pode ter no máximo ${MAX_DAYS} dias.`
  return ''
})
const range = computed(() => {
  if (isCustom.value) return { from: de.value, to: ate.value }
  const today = todayISO()
  return { from: addDays(today, -(presetDays.value - 1)), to: today }
})

function setQuery(next) {
  return router.push({ query: next })
}
const choosePreset = (n) => setQuery(n === 7 ? {} : { dias: n })
function chooseCustom() {
  const today = todayISO()
  setQuery({ de: addDays(today, -6), ate: today })
}

// ---- Dados do período --------------------------------------------------------------------
const days = ref([]) // ordem cronológica (como a API devolve)
const loading = ref(false)
const error = ref('')
let requestId = 0

async function load() {
  const id = ++requestId
  openDay.value = null
  if (rangeError.value) {
    days.value = []
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await getDailyMovements(range.value)
    if (id !== requestId) return // resposta antiga
    days.value = res.dias
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
    if (route.name === 'registro-diario') load()
  },
)

const products = useAsyncBlock(() => listAllProducts())
const dashboard = useAsyncBlock(getDashboard)
const productMap = computed(() => new Map((products.data.value ?? []).map((p) => [p.id, p])))
const daysAhead = computed(() => dashboard.data.value?.dias_antecedencia ?? 5)

onMounted(() => {
  load()
  products.load()
  dashboard.load()
})

// ---- Resumo ------------------------------------------------------------------------------
const rows = computed(() => days.value.slice().reverse()) // mais recente primeiro
const totalMovements = computed(() => days.value.reduce((s, d) => s + d.total_movimentacoes, 0))
const totalIn = computed(() => days.value.reduce((s, d) => s + Number(d.entradas), 0))
const totalOut = computed(() => days.value.reduce((s, d) => s + Number(d.saidas), 0))
const busiest = computed(() => {
  let best = null
  for (const d of days.value) if (d.total_movimentacoes > (best?.total_movimentacoes ?? 0)) best = d
  return best
})
const hasMovements = computed(() => totalMovements.value > 0)
// Há unidades diferentes somadas? (ou ainda não sabemos as unidades)
const mixedUnits = computed(() => {
  if (!productMap.value.size) return hasMovements.value
  const units = new Set()
  for (const d of days.value) for (const p of d.produtos ?? []) {
    if (p.total_movimentacoes) units.add(productMap.value.get(p.id)?.unit)
  }
  return units.size > 1
})

const balanceClass = (v) => {
  const n = Number(v)
  return n > 0 ? 'text-emerald-700' : n < 0 ? 'text-rose-700' : 'text-slate-500'
}
const signed = (v) => `${Number(v) > 0 ? '+' : ''}${formatDecimal(v)}`

// ---- Detalhe do dia (um por vez, sob demanda) ----------------------------------------------
const openDay = ref(null)
const detail = ref({ loading: false, error: '', items: [] })
let detailRequestId = 0

async function loadDetail(iso) {
  const id = ++detailRequestId
  detail.value = { loading: true, error: '', items: [] }
  try {
    const items = await listAllMovements({ from: iso, to: iso })
    if (id !== detailRequestId) return
    detail.value = { loading: false, error: '', items }
  } catch (err) {
    if (id !== detailRequestId) return
    detail.value = { loading: false, error: err.message, items: [] }
  }
}

function toggleDay(day) {
  if (openDay.value === day.data) {
    openDay.value = null
    return
  }
  openDay.value = day.data
  loadDetail(day.data)
}

const dayOf = (iso) => days.value.find((d) => d.data === iso)
const userNameOf = (iso, userId) => dayOf(iso)?.usuarios?.find((u) => u.id === userId)?.name ?? `Usuário #${userId}`
const productNameOf = (id) => productMap.value.get(id)?.name ?? `Produto #${id}`

// ---- Registro de movimentação (reaproveita o modal da F8) ---------------------------------------
const formOpen = ref(false)
function onSaved() {
  products.load()
  load() // fecha o detalhe aberto e recarrega o período
}

// ---- CSV do resumo -----------------------------------------------------------------------------
function exportCsv() {
  const header = ['Data', 'Entradas (qtd)', 'Saídas (qtd)', 'Saldo']
  const body = rows.value.map((d) => [formatDate(d.data), csvNumber(d.entradas), csvNumber(d.saidas), csvNumber(d.saldo)])
  downloadCsv(`registro-diario_${range.value.from}_${range.value.to}.csv`, [header, ...body])
}

const tabButton =
  'rounded-lg px-3 py-1.5 text-sm font-medium ring-1 ring-inset focus-visible:outline-2 focus-visible:outline-emerald-600'
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Resumo diário de tudo que entrou e saiu do estoque do haras.</p>
      <BaseButton @click="formOpen = true">Registrar movimentação</BaseButton>
    </div>

    <!-- Período -->
    <section class="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" aria-labelledby="titulo-periodo">
      <h2 id="titulo-periodo" class="mb-2 text-sm font-semibold text-slate-700">Período</h2>
      <div class="flex flex-wrap items-center gap-2" role="group" aria-labelledby="titulo-periodo">
        <button
          v-for="n in PRESETS"
          :key="n"
          type="button"
          :aria-pressed="!isCustom && presetDays === n"
          :class="[tabButton, !isCustom && presetDays === n ? 'bg-emerald-600 text-white ring-emerald-600' : 'bg-white text-slate-700 ring-slate-300 hover:bg-slate-50']"
          @click="choosePreset(n)"
        >
          Últimos {{ n }} dias
        </button>
        <button
          type="button"
          :aria-pressed="isCustom"
          :class="[tabButton, isCustom ? 'bg-emerald-600 text-white ring-emerald-600' : 'bg-white text-slate-700 ring-slate-300 hover:bg-slate-50']"
          @click="chooseCustom"
        >
          Personalizado
        </button>
      </div>
      <div v-if="isCustom" class="mt-3 grid gap-3 sm:max-w-md sm:grid-cols-2">
        <BaseInput label="De" type="date" :model-value="de" @update:model-value="setQuery({ de: $event, ate })" />
        <BaseInput
          label="Até"
          type="date"
          :model-value="ate"
          :error="rangeError"
          @update:model-value="setQuery({ de, ate: $event })"
        />
      </div>
    </section>

    <div v-if="error && !loading" class="rounded-xl bg-white ring-1 ring-slate-200">
      <ErrorState :message="error" @retry="load" />
    </div>
    <template v-else>
      <!-- Resumo do período -->
      <section aria-labelledby="titulo-resumo">
        <h2 id="titulo-resumo" class="sr-only">Resumo do período</h2>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Movimentações" :value="totalMovements" :loading="loading" />
          <StatCard title="Total de entradas" tone="emerald" :value="formatDecimal(totalIn)" :loading="loading" />
          <StatCard title="Total de saídas" tone="red" :value="formatDecimal(totalOut)" :loading="loading" />
          <StatCard
            title="Dia com mais movimento"
            :value="busiest ? formatDate(busiest.data) : '—'"
            :detail="busiest ? `${busiest.total_movimentacoes} movimentação(ões)` : ''"
            :loading="loading"
          />
        </div>
        <p v-if="mixedUnits && !loading" class="mt-2 text-xs text-slate-500">
          Quantidades somadas de unidades diferentes; veja o detalhe por produto.
        </p>
      </section>

      <!-- Gráfico -->
      <section class="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200" aria-labelledby="titulo-grafico">
        <h2 id="titulo-grafico" class="mb-3 text-base font-semibold text-slate-800">Entradas e saídas por dia</h2>
        <div v-if="loading" class="flex h-64 items-center justify-center text-emerald-600 sm:h-72"><Spinner /></div>
        <EmptyState v-else-if="!hasMovements" title="Sem movimentações no período" description="Escolha outro período ou registre uma movimentação." />
        <MovementsChart v-else :days="days" />
      </section>

      <!-- Dia a dia -->
      <section aria-labelledby="titulo-dias">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="titulo-dias" class="text-base font-semibold text-slate-800">Dia a dia</h2>
          <BaseButton variant="secondary" size="sm" :disabled="loading || !rows.length" @click="exportCsv">Exportar CSV</BaseButton>
        </div>
        <div class="overflow-x-auto rounded-xl bg-white ring-1 ring-slate-200">
          <table class="min-w-full divide-y divide-slate-200 text-sm">
            <caption class="sr-only">Registro diário de entradas e saídas</caption>
            <thead class="bg-slate-50">
              <tr>
                <th scope="col" class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-600">Data</th>
                <th scope="col" class="whitespace-nowrap px-4 py-3 text-right font-semibold text-slate-600">Movimentações</th>
                <th scope="col" class="whitespace-nowrap px-4 py-3 text-right font-semibold text-slate-600">Entradas (qtd)</th>
                <th scope="col" class="whitespace-nowrap px-4 py-3 text-right font-semibold text-slate-600">Saídas (qtd)</th>
                <th scope="col" class="whitespace-nowrap px-4 py-3 text-right font-semibold text-slate-600">Saldo do dia</th>
                <th scope="col" class="px-4 py-3"><span class="sr-only">Detalhes</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <template v-for="d in rows" :key="d.data">
                <tr :class="d.total_movimentacoes ? 'odd:bg-white even:bg-slate-50/60' : 'bg-slate-50/40 text-slate-400'">
                  <td class="whitespace-nowrap px-4 py-3 font-medium" :class="d.total_movimentacoes ? 'text-slate-800' : ''">
                    {{ formatDateWeekday(d.data) }}
                  </td>
                  <template v-if="d.total_movimentacoes">
                    <td class="px-4 py-3 text-right">{{ d.total_movimentacoes }}</td>
                    <td class="px-4 py-3 text-right text-emerald-700">{{ formatDecimal(d.entradas) }}</td>
                    <td class="px-4 py-3 text-right text-rose-700">{{ formatDecimal(d.saidas) }}</td>
                    <td class="px-4 py-3 text-right font-semibold" :class="balanceClass(d.saldo)">{{ signed(d.saldo) }}</td>
                    <td class="px-4 py-3 text-right">
                      <BaseButton
                        variant="secondary"
                        size="sm"
                        :aria-expanded="openDay === d.data"
                        :aria-controls="`detalhe-${d.data}`"
                        @click="toggleDay(d)"
                      >
                        {{ openDay === d.data ? 'Ocultar' : 'Ver detalhes' }}
                      </BaseButton>
                    </td>
                  </template>
                  <td v-else colspan="5" class="px-4 py-3 text-right italic">Sem movimentação</td>
                </tr>

                <tr v-if="openDay === d.data">
                  <td :id="`detalhe-${d.data}`" colspan="6" class="bg-slate-50 px-4 py-4">
                    <h3 class="mb-2 text-sm font-semibold text-slate-700">Por produto — {{ formatDate(d.data) }}</h3>
                    <ul class="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      <li v-for="p in d.produtos.filter((x) => x.total_movimentacoes)" :key="p.id" class="rounded-lg bg-white p-3 ring-1 ring-slate-200">
                        <p class="font-medium text-slate-800">{{ p.name }}</p>
                        <p class="text-xs text-slate-600">
                          Entradas {{ formatQuantity(p.entradas, productMap.get(p.id)?.unit) }} · Saídas
                          {{ formatQuantity(p.saidas, productMap.get(p.id)?.unit) }}
                        </p>
                        <p class="text-sm font-semibold" :class="balanceClass(p.saldo)">
                          Saldo {{ signed(p.saldo) }} {{ productMap.get(p.id)?.unit }}
                        </p>
                      </li>
                    </ul>

                    <h3 class="mb-2 text-sm font-semibold text-slate-700">Movimentações do dia</h3>
                    <div v-if="detail.loading" class="flex justify-center py-4 text-emerald-600"><Spinner /></div>
                    <ErrorState v-else-if="detail.error" :message="detail.error" @retry="loadDetail(d.data)" />
                    <EmptyState v-else-if="!detail.items.length" title="Nenhuma movimentação encontrada" />
                    <div v-else class="overflow-x-auto rounded-lg bg-white ring-1 ring-slate-200">
                      <table class="min-w-full divide-y divide-slate-200 text-sm">
                        <thead class="bg-slate-50 text-left text-slate-600">
                          <tr>
                            <th scope="col" class="px-3 py-2 font-semibold">Hora</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Tipo</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Produto</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Motivo</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Quantidade</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Usuário</th>
                            <th scope="col" class="px-3 py-2 font-semibold">Observação</th>
                          </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                          <tr v-for="m in detail.items" :key="m.id">
                            <td class="whitespace-nowrap px-3 py-2">{{ formatTime(new Date(m.created_at)) }}</td>
                            <td class="px-3 py-2">
                              <BaseBadge :tone="m.type === 'entrada' ? 'emerald' : 'rose'">{{ MOVEMENT_TYPES[m.type] ?? m.type }}</BaseBadge>
                            </td>
                            <td class="px-3 py-2">{{ productNameOf(m.product_id) }}</td>
                            <td class="px-3 py-2">{{ MOVEMENT_REASONS[m.reason] ?? m.reason }}</td>
                            <td class="whitespace-nowrap px-3 py-2">{{ formatQuantity(m.quantity, productMap.get(m.product_id)?.unit) }}</td>
                            <td class="px-3 py-2">{{ userNameOf(d.data, m.user_id) }}</td>
                            <td class="px-3 py-2">
                              <span v-if="m.note" class="block max-w-[14rem] truncate" :title="m.note">{{ m.note }}</span>
                              <span v-else>—</span>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
          <div v-if="loading" class="flex justify-center py-8 text-emerald-600"><Spinner /></div>
          <EmptyState v-else-if="!rows.length" :title="rangeError || 'Nenhum dia no período'" />
        </div>
      </section>
    </template>

    <MovementFormModal v-model="formOpen" :products="products.data.value ?? []" :days-ahead="daysAhead" @saved="onSaved" @conflict="products.load" />
  </div>
</template>
