<script setup>
import { computed, useId } from 'vue'
import { fieldClasses } from '../../utils/ui'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  rows: { type: Number, default: 3 },
  error: { type: String, default: '' },
  help: { type: String, default: '' },
  required: Boolean,
  id: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const autoId = useId()
const areaId = computed(() => props.id || autoId)
const describedBy = computed(() => {
  if (props.error) return `${areaId.value}-erro`
  if (props.help) return `${areaId.value}-ajuda`
  return undefined
})
</script>

<template>
  <div>
    <label v-if="label" :for="areaId" class="mb-1 block text-sm font-medium text-slate-700">
      {{ label }}<span v-if="required" class="text-red-600" aria-hidden="true"> *</span>
    </label>
    <textarea
      :id="areaId"
      v-bind="$attrs"
      :rows="rows"
      :value="modelValue"
      :aria-required="required || undefined"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      :class="fieldClasses(!!error)"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" :id="`${areaId}-erro`" class="mt-1 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="help" :id="`${areaId}-ajuda`" class="mt-1 text-sm text-slate-500">{{ help }}</p>
  </div>
</template>
