<script setup>
import { computed, ref, useId } from 'vue'
import { fieldClasses } from '../../utils/ui'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  products: { type: Array, default: () => [] },
  label: { type: String, default: 'Produto' },
  placeholder: { type: String, default: 'Selecione…' },
  error: { type: String, default: '' },
  required: Boolean,
})
const emit = defineEmits(['update:modelValue'])

const id = useId()
const term = ref('')
const searchInput = ref(null)
defineExpose({ focus: () => searchInput.value?.focus() })

// Filtra por nome ou código, mantendo sempre o item já selecionado na lista.
const options = computed(() => {
  const q = term.value.trim().toLowerCase()
  return props.products.filter(
    (p) =>
      String(p.id) === String(props.modelValue) ||
      !q ||
      p.name.toLowerCase().includes(q) ||
      (p.code ?? '').toLowerCase().includes(q),
  )
})
</script>

<template>
  <div>
    <label :for="`${id}-select`" class="mb-1 block text-sm font-medium text-slate-700">
      {{ label }}<span v-if="required" class="text-red-600" aria-hidden="true"> *</span>
    </label>
    <input
      ref="searchInput"
      v-model="term"
      type="search"
      :aria-label="`Buscar ${label.toLowerCase()} por nome ou código`"
      placeholder="Digite para filtrar a lista…"
      class="mb-1 text-sm"
      :class="fieldClasses(false)"
    />
    <select
      :id="`${id}-select`"
      :value="modelValue"
      :aria-required="required || undefined"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${id}-erro` : undefined"
      :class="fieldClasses(!!error)"
      @change="emit('update:modelValue', $event.target.value)"
    >
      <option value="">{{ placeholder }}</option>
      <option v-for="p in options" :key="p.id" :value="p.id">
        {{ p.name }}{{ p.active ? '' : ' (inativo)' }}
      </option>
    </select>
    <p v-if="term && !options.length" class="mt-1 text-sm text-slate-500">Nenhum produto encontrado.</p>
    <p v-if="error" :id="`${id}-erro`" class="mt-1 text-sm text-red-600">{{ error }}</p>
  </div>
</template>
