<script setup>
defineProps({
  title: { type: String, default: 'Nada por aqui' },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="flex flex-col items-center px-4 py-10 text-center">
    <svg class="size-10 text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 7l9-4 9 4v10l-9 4-9-4V7zM3 7l9 4m0 10V11m9-4-9 4" stroke-linejoin="round" />
    </svg>
    <p class="mt-3 font-medium text-slate-700">{{ title }}</p>
    <p v-if="description" class="mt-1 text-sm text-slate-500">{{ description }}</p>
    <div v-if="$slots.default" class="mt-4"><slot /></div>
  </div>
</template>
