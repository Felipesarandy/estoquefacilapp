<script setup>
defineProps({
  size: { type: String, default: 'md' }, // sm | md | lg
  label: { type: String, default: 'Carregando…' },
})
</script>

<template>
  <span role="status" class="inline-flex items-center">
    <svg
      class="animate-spin text-current"
      :class="{ 'size-4': size === 'sm', 'size-6': size === 'md', 'size-10': size === 'lg' }"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
    </svg>
    <span class="sr-only">{{ label }}</span>
  </span>
</template>
