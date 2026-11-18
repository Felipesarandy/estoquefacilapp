<script setup>
import BaseButton from './BaseButton.vue'

defineProps({
  message: { type: String, default: 'Não foi possível carregar.' },
  retryLabel: { type: String, default: 'Tentar novamente' },
})
defineEmits(['retry'])
</script>

<template>
  <div role="alert" class="flex flex-col items-center gap-3 px-4 py-8 text-center">
    <p class="text-sm text-red-700">{{ message }}</p>
    <BaseButton variant="secondary" size="sm" @click="$emit('retry')">{{ retryLabel }}</BaseButton>
  </div>
</template>
