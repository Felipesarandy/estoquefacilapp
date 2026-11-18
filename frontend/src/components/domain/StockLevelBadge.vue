<script setup>
import { computed } from 'vue'
import BaseBadge from '../ui/BaseBadge.vue'
import { STOCK_LEVELS } from '../../utils/constants'

const props = defineProps({
  level: { type: String, required: true }, // ruptura | critico | atencao | ok
})

const info = computed(() => STOCK_LEVELS[props.level] ?? { label: props.level, classes: '' })
</script>

<template>
  <BaseBadge :custom-class="info.classes">{{ info.label }}</BaseBadge>
</template>
