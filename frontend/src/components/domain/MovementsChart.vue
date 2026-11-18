<script setup>
import { computed } from 'vue'
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import { Bar } from 'vue-chartjs'
import { formatDayMonth } from '../../utils/format'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

const props = defineProps({
  days: { type: Array, required: true }, // [{ data, entradas, saidas }] (decimais como texto)
})

const chartData = computed(() => ({
  labels: props.days.map((d) => formatDayMonth(d.data)),
  datasets: [
    { label: 'Entradas', backgroundColor: '#10b981', borderRadius: 4, data: props.days.map((d) => Number(d.entradas)) },
    { label: 'Saídas', backgroundColor: '#f43f5e', borderRadius: 4, data: props.days.map((d) => Number(d.saidas)) },
  ],
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' } },
  scales: { y: { beginAtZero: true } },
}

const ariaLabel = computed(() => {
  const resumo = props.days
    .map((d) => `${formatDayMonth(d.data)}: ${Number(d.entradas)} de entrada e ${Number(d.saidas)} de saída`)
    .join('; ')
  return `Gráfico de barras de entradas e saídas dos últimos ${props.days.length} dias. ${resumo}.`
})
</script>

<template>
  <div class="h-64 sm:h-72">
    <Bar :data="chartData" :options="options" role="img" :aria-label="ariaLabel" />
  </div>
</template>
