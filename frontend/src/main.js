import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/http'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 401 fora do login: encerra a sessão e volta ao login guardando a rota atual.
setUnauthorizedHandler(() => {
  useAuthStore().logout()
  const current = router.currentRoute.value
  // Sem nome = navegação inicial ainda em curso; o guard do router cuida do redirecionamento.
  if (!current.name || current.name === 'login') return
  router.push({ name: 'login', query: { redirect: current.fullPath } })
})

app.mount('#app')
