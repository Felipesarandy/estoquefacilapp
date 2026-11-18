<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useToastStore } from './stores/toast'

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

function sair() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <!-- Barra provisória para testar o fluxo; será substituída pelo layout da F3. -->
  <div
    v-if="auth.isAuthenticated"
    class="flex items-center justify-between gap-3 bg-emerald-700 px-4 py-2 text-sm text-white"
  >
    <span>{{ auth.user.name }} ({{ auth.user.role }})</span>
    <button
      type="button"
      class="rounded bg-white/15 px-3 py-1 font-medium hover:bg-white/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      @click="sair"
    >
      Sair
    </button>
  </div>

  <main class="p-4">
    <RouterView />
  </main>

  <div class="fixed right-4 top-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
    <div
      v-for="t in toast.toasts"
      :key="t.id"
      role="status"
      class="flex items-start justify-between gap-2 rounded-lg px-4 py-3 text-sm shadow-lg"
      :class="{
        'bg-red-600 text-white': t.type === 'error',
        'bg-amber-500 text-white': t.type === 'warning',
        'bg-emerald-600 text-white': t.type === 'success',
        'bg-slate-800 text-white': t.type === 'info',
      }"
    >
      <span>{{ t.message }}</span>
      <button type="button" class="font-bold" aria-label="Fechar aviso" @click="toast.dismiss(t.id)">×</button>
    </div>
  </div>
</template>
