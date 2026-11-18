<script setup>
import EmptyState from './EmptyState.vue'
import Spinner from './Spinner.vue'

defineProps({
  columns: { type: Array, required: true }, // [{ key, label, class? }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' },
  loading: Boolean,
  caption: { type: String, default: '' },
  emptyTitle: { type: String, default: 'Nenhum registro encontrado' },
  emptyDescription: { type: String, default: '' },
})
</script>

<template>
  <div class="overflow-x-auto rounded-xl bg-white ring-1 ring-slate-200">
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <caption v-if="caption" class="sr-only">{{ caption }}</caption>
      <thead class="bg-slate-50">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            scope="col"
            class="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-600"
            :class="col.class"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="row in rows" :key="row[rowKey]" class="odd:bg-white even:bg-slate-50/60">
          <td v-for="col in columns" :key="col.key" class="px-4 py-3 text-slate-700" :class="col.class">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">{{ row[col.key] ?? '—' }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="loading" class="flex justify-center py-8 text-emerald-600"><Spinner /></div>
    <EmptyState v-else-if="!rows.length" :title="emptyTitle" :description="emptyDescription" />
  </div>
</template>
