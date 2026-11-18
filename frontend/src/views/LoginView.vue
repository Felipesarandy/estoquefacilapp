<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthLayout from '../layouts/AuthLayout.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const formError = ref('')
const loading = ref(false)
const emailInput = ref(null)

onMounted(() => emailInput.value?.focus())

function validate() {
  errors.email = ''
  errors.password = ''
  const email = form.email.trim()
  if (!email) errors.email = 'Informe o e-mail.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Informe um e-mail válido.'
  if (!form.password) errors.password = 'Informe a senha.'
  return !errors.email && !errors.password
}

async function submit() {
  formError.value = ''
  if (!validate()) return
  loading.value = true
  try {
    await auth.login(form.email.trim(), form.password)
    const redirect = route.query.redirect
    // Só aceita caminhos internos para evitar redirecionamento aberto.
    const target = typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/'
    await router.replace(target)
  } catch (err) {
    errors.email = err.fields?.email ?? ''
    errors.password = err.fields?.password ?? ''
    if (!errors.email && !errors.password) formError.value = err.message
  } finally {
    loading.value = false
  }
}

const inputBase =
  'mt-1 block w-full rounded-lg border px-3 py-2 text-slate-900 shadow-sm focus:outline-2 focus:outline-offset-1 focus:outline-emerald-600'
</script>

<template>
  <AuthLayout>
    <h2 class="mb-6 text-xl font-semibold text-slate-800">Entrar</h2>

    <form novalidate class="space-y-5" @submit.prevent="submit">
      <div
        v-if="formError"
        role="alert"
        class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200"
      >
        {{ formError }}
      </div>

      <div>
        <label for="email" class="block text-sm font-medium text-slate-700">E-mail</label>
        <input
          id="email"
          ref="emailInput"
          v-model="form.email"
          type="email"
          autocomplete="username"
          :aria-invalid="!!errors.email"
          :aria-describedby="errors.email ? 'email-erro' : undefined"
          :class="[inputBase, errors.email ? 'border-red-500' : 'border-slate-300']"
        />
        <p v-if="errors.email" id="email-erro" class="mt-1 text-sm text-red-600">{{ errors.email }}</p>
      </div>

      <div>
        <label for="password" class="block text-sm font-medium text-slate-700">Senha</label>
        <input
          id="password"
          v-model="form.password"
          type="password"
          autocomplete="current-password"
          :aria-invalid="!!errors.password"
          :aria-describedby="errors.password ? 'senha-erro' : undefined"
          :class="[inputBase, errors.password ? 'border-red-500' : 'border-slate-300']"
        />
        <p v-if="errors.password" id="senha-erro" class="mt-1 text-sm text-red-600">{{ errors.password }}</p>
      </div>

      <button
        type="submit"
        :disabled="loading"
        class="w-full rounded-lg bg-emerald-600 px-4 py-2.5 font-medium text-white hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {{ loading ? 'Entrando…' : 'Entrar' }}
      </button>
    </form>
  </AuthLayout>
</template>
