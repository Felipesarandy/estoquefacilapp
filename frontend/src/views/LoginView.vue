<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '../components/ui/BaseButton.vue'
import BaseInput from '../components/ui/BaseInput.vue'
import { useApiForm } from '../composables/useApiForm'
import AuthLayout from '../layouts/AuthLayout.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ email: '', password: '' })
const { errors, formError, submitting, submit: runSubmit } = useApiForm(form)
const emailInput = ref(null)

onMounted(() => emailInput.value?.focus())

function validate() {
  delete errors.email
  delete errors.password
  const email = form.email.trim()
  if (!email) errors.email = 'Informe o e-mail.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Informe um e-mail válido.'
  if (!form.password) errors.password = 'Informe a senha.'
  return !errors.email && !errors.password
}

// Só aceita caminhos internos para evitar redirecionamento aberto.
function redirectTarget() {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
    ? redirect
    : '/'
}

async function submit() {
  if (!validate()) return
  await runSubmit(async () => {
    await auth.login(form.email.trim(), form.password)
    await router.replace(redirectTarget())
  })
}
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

      <BaseInput
        ref="emailInput"
        v-model="form.email"
        label="E-mail"
        type="email"
        autocomplete="username"
        :error="errors.email"
      />
      <BaseInput
        v-model="form.password"
        label="Senha"
        type="password"
        autocomplete="current-password"
        :error="errors.password"
      />

      <BaseButton type="submit" block size="lg" :loading="submitting">
        {{ submitting ? 'Entrando…' : 'Entrar' }}
      </BaseButton>
    </form>
  </AuthLayout>
</template>
