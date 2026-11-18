<script setup>
import { computed } from 'vue'
import Spinner from './Spinner.vue'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | danger
  size: { type: String, default: 'md' }, // sm | md | lg
  type: { type: String, default: 'button' },
  loading: Boolean,
  disabled: Boolean,
  block: Boolean,
})

const variants = {
  primary: 'bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:outline-emerald-600',
  secondary:
    'bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus-visible:outline-emerald-600',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600',
}
const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
}
const classes = computed(() => [
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60',
  variants[props.variant],
  sizes[props.size],
  props.block && 'w-full',
])
</script>

<template>
  <button :type="type" :disabled="disabled || loading" :aria-busy="loading || undefined" :class="classes">
    <Spinner v-if="loading" size="sm" label="Aguarde…" />
    <slot />
  </button>
</template>
