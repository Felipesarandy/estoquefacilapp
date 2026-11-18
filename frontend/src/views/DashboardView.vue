<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { listAlerts } from '../api/alerts'
import { getDashboard } from '../api/dashboard'
import { getIncidentsSummary } from '../api/incidents'
import { getDailyMovements, listMovements } from '../api/movements'
import { listProducts } from '../api/products'
import MovementsChart from '../components/domain/MovementsChart.vue'
import StatCard from '../components/domain/StatCard.vue'
import StockLevelBadge from '../components/domain/StockLevelBadge.vue'
import BaseBadge from '../components/ui/BaseBadge.vue'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseTable from '../components/ui/BaseTable.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import ErrorState from '../components/ui/ErrorState.vue'
import Spinner from '../components/ui/Spinner.vue'
import { useAsyncBlock } from '../composables/useAsyncBlock'
import { MOVEMENT_REASONS, MOVEMENT_TYPES, STOCK_LEVELS } from '../utils/constants'
import { addDays, formatDateTime, formatDecimal, formatQuantity, todayISO } from '../utils/format'

const DAYS = 7
const ATTENTION_ROWS = 8
const LAST_MOVEMENTS = 5
const LEVELS = ['ruptura', 'critico', 'atencao', 'ok']

const summary = useAsyncBlock(getDashboard)
const alerts = useAsyncBlock(() => listAlerts({ per_page: ATTENTION_ROWS }))
const daily = useAsyncBlock(() => {
  const today = todayISO()
  return getDailyMovements({ from: addDays(today, -(DAYS - 1)), to: today })
})
const incidents = useAsyncBlock(getIncidentsSummary)
const movements = useAsyncBlock(() => listMovements({ per_page: LAST_MOVEMENTS }))
// A API devolve só product_id nas movimentações; os nomes vêm da lista de produtos (sem filtro de situação, então inclui os inativos).
const products = useAsyncBlock(() => listProducts({ per_page: 100 }))

const blocks = [summary, alerts, daily, incidents, movements, products]
const anyLoading = computed(() => blocks.some((b) => b.loading.value))

function loadAll() {
  return Promise.allSettled(blocks.map((b) => b.load()))
}
onMounted(loadAll)

const productNames = computed(
  () => new Map((products.data.value?.items ?? []).map((p) => [p.id, p.name])),
)
const productName = (id) => productNames.value.get(id) ?? `Produto #${id}`

const incidentsOpen = computed(() => {
  const s = incidents.data.value?.por_status ?? {}
  return (s.aberto ?? 0) + (s.em_analise ?? 0)
})
const today = computed(() => summary.data.value?.movimentacoes_hoje)
const todayDetail = computed(() =>
  today.value
    ? `Entradas ${formatDecimal(today.value.entradas)} · Saídas ${formatDecimal(today.value.saidas)}`
    : '',
)

const chartDays = computed(() => daily.data.value?.dias ?? [])
const hasChartData = computed(() => chartDays.value.some((d) => Number(d.entradas) || Number(d.saidas)))

const attentionColumns = [
  { key: 'name', label: 'Produto' },
  { key: 'nivel', label: 'Nível' },
  { key: 'current_stock', label: 'Estoque atual' },
  { key: 'min_stock', label: 'Mínimo' },
  { key: 'cobertura_dias', label: 'Cobertura' },
]
const coverage = (row) =>
  row.cobertura_dias === null || row.cobertura_dias === undefined
    ? '—'
    : `${formatDecimal(row.cobertura_dias)} dia(s)`
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-3">
      <p class="text-sm text-slate-600">Situação do estoque e movimento recente.</p>
      <BaseButton variant="secondary" size="sm" :loading="anyLoading" @click="loadAll">Atualizar</BaseButton>
    </div>

    <!-- a) Indicadores -->
    <section aria-labelledby="titulo-indicadores">
      <h2 id="titulo-indicadores" class="sr-only">Indicadores</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4">
        <StatCard
          title="Produtos ativos"
          tone="slate"
          :value="summary.data.value?.produtos_ativos ?? '—'"
          :loading="summary.loading.value"
        />
        <StatCard
          v-for="level in LEVELS.slice(0, 3)"
          :key="level"
          :title="STOCK_LEVELS[level].label"
          :tone="STOCK_LEVELS[level].tone"
          :value="summary.data.value?.por_nivel?.[level] ?? '—'"
          :to="{ name: 'alertas' }"
          :loading="summary.loading.value"
        />
        <StatCard
          :title="STOCK_LEVELS.ok.label"
          :tone="STOCK_LEVELS.ok.tone"
          :value="summary.data.value?.por_nivel?.ok ?? '—'"
          :loading="summary.loading.value"
        />
        <StatCard
          title="Incidentes abertos"
          tone="sky"
          :value="incidents.data.value ? incidentsOpen : '—'"
          :detail="incidents.error.value ? 'Falha ao carregar' : 'Abertos ou em análise'"
          :to="{ name: 'incidentes' }"
          :loading="incidents.loading.value"
        />
        <StatCard
          title="Movimentações hoje"
          :value="today?.total_movimentacoes ?? '—'"
          :detail="todayDetail"
          :loading="summary.loading.value"
        />
      </div>
      <ErrorState
        v-if="summary.error.value && !summary.loading.value"
        :message="summary.error.value"
        @retry="summary.load"
      />
      <ErrorState
        v-if="incidents.error.value && !incidents.loading.value"
        :message="incidents.error.value"
        @retry="incidents.load"
      />
    </section>

    <div class="grid gap-6 xl:grid-cols-2">
      <!-- b) Gráfico -->
      <section aria-labelledby="titulo-grafico" class="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <h2 id="titulo-grafico" class="text-base font-semibold text-slate-800">
          Entradas e saídas — últimos {{ DAYS }} dias
        </h2>
        <p class="mb-3 text-xs text-slate-500">Quantidades somadas, independentemente da unidade.</p>
        <div class="min-h-64 sm:min-h-72">
          <div v-if="daily.loading.value" class="flex h-64 items-center justify-center text-emerald-600 sm:h-72">
            <Spinner />
          </div>
          <ErrorState v-else-if="daily.error.value" :message="daily.error.value" @retry="daily.load" />
          <EmptyState
            v-else-if="!hasChartData"
            title="Sem movimentações no período"
            description="As entradas e saídas aparecerão aqui."
          />
          <MovementsChart v-else :days="chartDays" />
        </div>
      </section>

      <!-- d) Últimas movimentações -->
      <section aria-labelledby="titulo-movs" class="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="mb-3 flex items-center justify-between">
          <h2 id="titulo-movs" class="text-base font-semibold text-slate-800">Últimas movimentações</h2>
          <RouterLink
            :to="{ name: 'movimentacoes' }"
            class="text-sm font-medium text-emerald-700 hover:underline focus-visible:outline-2 focus-visible:outline-emerald-600"
          >
            Ver todas
          </RouterLink>
        </div>
        <div class="min-h-64">
          <div v-if="movements.loading.value" class="flex h-64 items-center justify-center text-emerald-600">
            <Spinner />
          </div>
          <ErrorState v-else-if="movements.error.value" :message="movements.error.value" @retry="movements.load" />
          <EmptyState v-else-if="!movements.data.value?.items.length" title="Nenhuma movimentação registrada" />
          <ul v-else class="divide-y divide-slate-100">
            <li v-for="m in movements.data.value.items" :key="m.id" class="flex items-center justify-between gap-3 py-3">
              <div class="min-w-0">
                <p class="truncate font-medium text-slate-800">{{ productName(m.product_id) }}</p>
                <p class="text-xs text-slate-500">
                  {{ formatDateTime(m.created_at) }} · {{ MOVEMENT_REASONS[m.reason] ?? m.reason }}
                </p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <span class="text-sm font-medium text-slate-700">{{ formatDecimal(m.quantity) }}</span>
                <BaseBadge :tone="m.type === 'entrada' ? 'emerald' : 'rose'">
                  {{ MOVEMENT_TYPES[m.type] ?? m.type }}
                </BaseBadge>
              </div>
            </li>
          </ul>
        </div>
      </section>
    </div>

    <!-- c) Produtos que precisam de atenção -->
    <section aria-labelledby="titulo-atencao">
      <div class="mb-3 flex items-center justify-between">
        <h2 id="titulo-atencao" class="text-base font-semibold text-slate-800">
          Produtos que precisam de atenção
        </h2>
        <RouterLink
          :to="{ name: 'alertas' }"
          class="text-sm font-medium text-emerald-700 hover:underline focus-visible:outline-2 focus-visible:outline-emerald-600"
        >
          Ver todos
        </RouterLink>
      </div>
      <div v-if="alerts.error.value && !alerts.loading.value" class="rounded-xl bg-white ring-1 ring-slate-200">
        <ErrorState :message="alerts.error.value" @retry="alerts.load" />
      </div>
      <BaseTable
        v-else
        caption="Produtos em ruptura, crítico ou atenção"
        :columns="attentionColumns"
        :rows="alerts.data.value?.items ?? []"
        :loading="alerts.loading.value"
        empty-title="Nenhum produto em alerta"
        empty-description="Todo o estoque está dentro do esperado."
      >
        <template #cell-name="{ row }">
          <span class="font-medium text-slate-800">{{ row.name }}</span>
          <span class="block text-xs text-slate-500">{{ row.code }}</span>
        </template>
        <template #cell-nivel="{ row }"><StockLevelBadge :level="row.nivel" /></template>
        <template #cell-current_stock="{ row }">{{ formatQuantity(row.current_stock, row.unit) }}</template>
        <template #cell-min_stock="{ row }">{{ formatQuantity(row.min_stock, row.unit) }}</template>
        <template #cell-cobertura_dias="{ row }">{{ coverage(row) }}</template>
      </BaseTable>
    </section>
  </div>
</template>
