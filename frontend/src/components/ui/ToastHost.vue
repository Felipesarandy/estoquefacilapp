<script setup>
import { useToastStore } from '../../stores/toast'

const toast = useToastStore()
</script>

<template>
  <div
    class="fixed right-4 top-4 z-[100] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
    aria-live="polite"
  >
    <div
      v-for="t in toast.toasts"
      :key="t.id"
      role="status"
      class="flex items-start justify-between gap-2 rounded-lg px-4 py-3 text-sm shadow-lg"
      :class="{
        'bg-red-600 text-white': t.type === 'error',
        'bg-amber-500 text-white': t.type === 'warning',
        'bg-emerald-600 text-white': t.type === 'success',
        'bg-slate-800 text-white': t.type === 'info',
      }"
    >
      <span>{{ t.message }}</span>
      <button
        type="button"
        class="rounded px-1 font-bold focus-visible:outline-2 focus-visible:outline-white"
        aria-label="Fechar aviso"
        @click="toast.dismiss(t.id)"
      >
        ×
      </button>
    </div>
  </div>
</template>
