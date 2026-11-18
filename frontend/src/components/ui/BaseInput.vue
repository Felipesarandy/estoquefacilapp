<script setup>
import { computed, ref, useId } from 'vue'
import { fieldClasses } from '../../utils/ui'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  error: { type: String, default: '' },
  help: { type: String, default: '' },
  required: Boolean,
  id: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const autoId = useId()
const inputId = computed(() => props.id || autoId)
const describedBy = computed(() => {
  if (props.error) return `${inputId.value}-erro`
  if (props.help) return `${inputId.value}-ajuda`
  return undefined
})

const input = ref(null)
defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <div>
    <label v-if="label" :for="inputId" class="mb-1 block text-sm font-medium text-slate-700">
      {{ label }}<span v-if="required" class="text-red-600" aria-hidden="true"> *</span>
    </label>
    <input
      :id="inputId"
      ref="input"
      v-bind="$attrs"
      :type="type"
      :value="modelValue"
      :aria-required="required || undefined"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      :class="fieldClasses(!!error)"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" :id="`${inputId}-erro`" class="mt-1 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="help" :id="`${inputId}-ajuda`" class="mt-1 text-sm text-slate-500">{{ help }}</p>
  </div>
</template>
