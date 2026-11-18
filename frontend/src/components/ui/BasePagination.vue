<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  perPage: { type: Number, default: 20 },
  total: { type: Number, default: 0 },
})
const emit = defineEmits(['update:page'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))
const from = computed(() => (props.total ? (props.page - 1) * props.perPage + 1 : 0))
const to = computed(() => Math.min(props.page * props.perPage, props.total))

// Janela de até 5 páginas ao redor da atual.
const pages = computed(() => {
  const start = Math.max(1, Math.min(props.page - 2, totalPages.value - 4))
  const end = Math.min(totalPages.value, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

function go(p) {
  if (p >= 1 && p <= totalPages.value && p !== props.page) emit('update:page', p)
}

const btn =
  'rounded-lg px-3 py-1.5 text-sm font-medium ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-50'
</script>

<template>
  <nav class="flex flex-col items-center justify-between gap-3 sm:flex-row" aria-label="Paginação">
    <p class="text-sm text-slate-600">
      <template v-if="total">Mostrando {{ from }}–{{ to }} de {{ total }}</template>
      <template v-else>Nenhum registro</template>
    </p>
    <div v-if="totalPages > 1" class="flex flex-wrap items-center gap-1">
      <button type="button" :class="btn" :disabled="page <= 1" @click="go(page - 1)">Anterior</button>
      <button
        v-for="p in pages"
        :key="p"
        type="button"
        :class="[btn, p === page && '!bg-emerald-600 !text-white !ring-emerald-600']"
        :aria-current="p === page ? 'page' : undefined"
        :aria-label="`Página ${p}`"
        @click="go(p)"
      >
        {{ p }}
      </button>
      <button type="button" :class="btn" :disabled="page >= totalPages" @click="go(page + 1)">Próxima</button>
    </div>
  </nav>
</template>
