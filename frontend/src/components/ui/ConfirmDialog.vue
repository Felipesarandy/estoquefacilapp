<script setup>
import BaseButton from './BaseButton.vue'
import BaseModal from './BaseModal.vue'

defineProps({
  modelValue: Boolean,
  title: { type: String, default: 'Confirmar' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  cancelLabel: { type: String, default: 'Cancelar' },
  danger: Boolean,
  loading: Boolean,
})
const emit = defineEmits(['update:modelValue', 'confirm'])
</script>

<template>
  <BaseModal :model-value="modelValue" :title="title" size="sm" @update:model-value="emit('update:modelValue', $event)">
    <p class="text-sm text-slate-600">{{ message }}<slot /></p>
    <template #footer>
      <BaseButton variant="secondary" :disabled="loading" @click="emit('update:modelValue', false)">
        {{ cancelLabel }}
      </BaseButton>
      <BaseButton :variant="danger ? 'danger' : 'primary'" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
