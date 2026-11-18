<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  detail: { type: String, default: '' },
  tone: { type: String, default: '' }, // slate | emerald | amber | orange | red | sky (vazio = sem destaque)
  to: { type: [String, Object], default: null }, // se informado, o cartão vira link
  loading: Boolean,
  active: Boolean, // destaca o cartão (ex.: filtro selecionado)
})

const tones = {
  slate: 'border-l-4 border-l-slate-400',
  emerald: 'border-l-4 border-l-emerald-500',
  amber: 'border-l-4 border-l-amber-500',
  orange: 'border-l-4 border-l-orange-500',
  red: 'border-l-4 border-l-red-500',
  sky: 'border-l-4 border-l-sky-500',
}
const valueTones = {
  emerald: 'text-emerald-700',
  amber: 'text-amber-700',
  orange: 'text-orange-700',
  red: 'text-red-700',
  sky: 'text-sky-700',
}

const tag = computed(() => (props.to ? RouterLink : 'div'))
const bindings = computed(() => (props.to ? { to: props.to } : {}))
</script>

<template>
  <component
    :is="tag"
    v-bind="bindings"
    :aria-busy="loading || undefined"
    :aria-current="active ? 'true' : undefined"
    class="block rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200"
    :class="[
      tones[tone],
      active && 'ring-2 ring-emerald-600',
      to && 'transition hover:shadow-md hover:ring-slate-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600',
    ]"
  >
    <p class="text-sm font-medium text-slate-500">{{ title }}</p>
    <p class="mt-2 text-3xl font-bold" :class="valueTones[tone] || 'text-slate-800'">
      {{ loading ? '…' : value }}
    </p>
    <p v-if="detail && !loading" class="mt-1 text-sm text-slate-500">{{ detail }}</p>
  </component>
</template>
