import { ref } from 'vue'
import { defineStore } from 'pinia'

const DEFAULT_DURATION = 4000

export const useToastStore = defineStore('toast', () => {
  const toasts = ref([])
  let nextId = 1

  /** type: 'info' | 'success' | 'warning' | 'error'. Não repete aviso idêntico já visível. */
  function push(message, type = 'info', duration = DEFAULT_DURATION) {
    if (toasts.value.some((t) => t.message === message && t.type === type)) return
    const id = nextId++
    toasts.value.push({ id, message, type })
    if (duration) setTimeout(() => dismiss(id), duration)
  }

  function dismiss(id) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return {
    toasts,
    push,
    dismiss,
    info: (m) => push(m, 'info'),
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'error'),
    warning: (m) => push(m, 'warning'),
  }
})
