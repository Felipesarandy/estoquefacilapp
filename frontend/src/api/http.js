import axios from 'axios'

export const TOKEN_KEY = 'estoquefacil_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

/** Erro normalizado lançado por todas as chamadas à API. */
export class ApiError extends Error {
  constructor({ status = 0, message, fields = {}, details = null }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
    this.details = details
  }
}

// Callback registrado pelo app (evita importar o router aqui e criar ciclo).
let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      return Promise.reject(
        new ApiError({ status: 0, message: 'Não foi possível conectar ao servidor' }),
      )
    }
    const { status, data } = error.response
    const apiError = data?.error ?? {}
    const details = apiError.details ?? null
    const fields = {}
    if (details?.field) fields[details.field] = apiError.message

    const isLogin = error.config?.url?.includes('/auth/login')
    if (status === 401 && !isLogin) {
      clearToken()
      onUnauthorized?.()
    }

    return Promise.reject(
      new ApiError({
        status,
        message: apiError.message ?? 'Erro inesperado. Tente novamente.',
        fields,
        details,
      }),
    )
  },
)

export default http
