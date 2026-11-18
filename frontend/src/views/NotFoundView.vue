<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-100 px-4 text-center">
    <p class="text-5xl font-bold text-emerald-700">404</p>
    <h1 class="text-xl font-semibold text-slate-800">Página não encontrada</h1>
    <p class="max-w-sm text-sm text-slate-600">O endereço que você tentou abrir não existe ou foi movido.</p>
    <RouterLink
      :to="{ name: 'dashboard' }"
      class="mt-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
    >
      Voltar ao início
    </RouterLink>
  </section>
</template>
