<script setup>
defineProps({
  tone: { type: String, default: 'slate' }, // slate | emerald | amber | orange | red | rose | sky | indigo
  customClass: { type: String, default: '' }, // sobrescreve o tom (ex.: classes de utils/constants.js)
})

const tones = {
  slate: 'bg-slate-100 text-slate-700 ring-slate-500/20',
  emerald: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
  amber: 'bg-amber-100 text-amber-800 ring-amber-600/20',
  orange: 'bg-orange-100 text-orange-800 ring-orange-600/20',
  rose: 'bg-rose-100 text-rose-800 ring-rose-600/20',
  red: 'bg-red-100 text-red-800 ring-red-600/20',
  sky: 'bg-sky-100 text-sky-800 ring-sky-600/20',
  indigo: 'bg-indigo-100 text-indigo-800 ring-indigo-600/20',
}
</script>

<template>
  <span
    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset"
    :class="customClass || tones[tone]"
  >
    <slot />
  </span>
</template>
