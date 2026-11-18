<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  detail: { type: String, default: '' },
})
</script>

<template>
  <div class="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
    <p class="text-sm font-medium text-slate-500">{{ title }}</p>
    <p class="mt-2 text-3xl font-bold text-slate-800">{{ value }}</p>
    <p v-if="detail" class="mt-1 text-sm text-slate-500">{{ detail }}</p>
  </div>
</template>
