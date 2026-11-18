<script setup>
import { computed, useId } from 'vue'
import { fieldClasses } from '../../utils/ui'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] }, // [{ value, label }]
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  error: { type: String, default: '' },
  help: { type: String, default: '' },
  required: Boolean,
  id: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const autoId = useId()
const selectId = computed(() => props.id || autoId)
const describedBy = computed(() => {
  if (props.error) return `${selectId.value}-erro`
  if (props.help) return `${selectId.value}-ajuda`
  return undefined
})
</script>

<template>
  <div>
    <label v-if="label" :for="selectId" class="mb-1 block text-sm font-medium text-slate-700">
      {{ label }}<span v-if="required" class="text-red-600" aria-hidden="true"> *</span>
    </label>
    <select
      :id="selectId"
      v-bind="$attrs"
      :value="modelValue"
      :aria-required="required || undefined"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      :class="fieldClasses(!!error)"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <slot>
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </slot>
    </select>
    <p v-if="error" :id="`${selectId}-erro`" class="mt-1 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="help" :id="`${selectId}-ajuda`" class="mt-1 text-sm text-slate-500">{{ help }}</p>
  </div>
</template>
