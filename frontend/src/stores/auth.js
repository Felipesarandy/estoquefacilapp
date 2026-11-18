import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '../api/auth'
import { clearToken, getToken, setToken } from '../api/http'
import { SESSION_EXPIRED_MESSAGE } from '../utils/constants'
import { useToastStore } from './toast'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref(null)
  let initPromise = null

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function clearSession() {
    token.value = null
    user.value = null
    clearToken()
  }

  async function login(email, password) {
    const data = await authApi.login(email, password)
    setToken(data.access_token)
    token.value = data.access_token
    user.value = data.user
  }

  async function fetchMe() {
    user.value = await authApi.getMe()
  }

  function logout() {
    clearSession()
  }

  /** Restaura a sessão ao abrir o app (uma única vez). */
  function init() {
    if (!initPromise) {
      initPromise = (async () => {
        if (!token.value) return
        try {
          await fetchMe()
        } catch (err) {
          clearSession()
          // Erro de rede não é sessão expirada.
          if (err?.status === 401) useToastStore().warning(SESSION_EXPIRED_MESSAGE)
        }
      })()
    }
    return initPromise
  }

  return { token, user, isAuthenticated, isAdmin, login, fetchMe, logout, init }
})
