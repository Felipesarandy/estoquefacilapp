<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { createUser, updateUser } from '../../api/users'
import { useApiForm } from '../../composables/useApiForm'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import { ROLES } from '../../utils/constants'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseSelect from '../ui/BaseSelect.vue'

const PASSWORD_MIN = 8 // regra real da API (schemas/users.py)

const props = defineProps({
  modelValue: Boolean,
  user: { type: Object, default: null }, // null = criar
})
const emit = defineEmits(['update:modelValue', 'saved'])

const auth = useAuthStore()
const toast = useToastStore()
const form = reactive({ name: '', email: '', role: 'tratador', password: '', confirm: '' })
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const showPasswords = ref(false)
const firstField = ref(null)

const isEdit = computed(() => !!props.user)
const isSelf = computed(() => !!props.user && props.user.id === auth.user?.id)
const roleOptions = Object.entries(ROLES).map(([value, { label }]) => ({ value, label }))

function clearSecrets() {
  form.password = ''
  form.confirm = ''
  showPasswords.value = false
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) {
      clearSecrets() // nunca mantém senha depois de fechar
      return
    }
    reset()
    clearSecrets()
    form.name = props.user?.name ?? ''
    form.email = props.user?.email ?? ''
    form.role = props.user?.role ?? 'tratador'
    await nextTick()
    await nextTick()
    firstField.value?.focus()
  },
)

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  const name = form.name.trim()
  if (!name) errors.name = 'Informe o nome.'
  else if (name.length > 120) errors.name = 'O nome deve ter até 120 caracteres.'
  if (!isEdit.value) {
    const email = form.email.trim()
    if (!email) errors.email = 'Informe o e-mail.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Informe um e-mail válido.'
  }
  if (!form.role) errors.role = 'Selecione o perfil.'
  // Criação: senha obrigatória. Edição: só valida se o campo foi preenchido (redefinição).
  if (!isEdit.value || form.password || form.confirm) {
    if (!form.password) errors.password = 'Informe a senha.'
    else if (form.password.length < PASSWORD_MIN) errors.password = `A senha deve ter pelo menos ${PASSWORD_MIN} caracteres.`
    else if (form.password.length > 200) errors.password = 'A senha deve ter até 200 caracteres.'
    if (!errors.password && form.confirm !== form.password) errors.confirm = 'A confirmação não é igual à senha.'
  }
  return Object.keys(errors).length === 0
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  const editing = isEdit.value
  const ok = await submit(async () => {
    try {
      if (editing) {
        const payload = { name: form.name.trim() }
        if (!isSelf.value) payload.role = form.role // a API recusa mudar o próprio perfil
        if (form.password) payload.password = form.password
        await updateUser(props.user.id, payload)
      } else {
        await createUser({ name: form.name.trim(), email: form.email.trim(), role: form.role, password: form.password })
      }
    } catch (err) {
      if (err.status === 409 && !editing) err.fields = { email: err.message } // e-mail duplicado
      else if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  clearSecrets()
  if (!ok) return
  toast.success(editing ? 'Usuário atualizado.' : 'Usuário cadastrado.')
  if (editing && isSelf.value) auth.fetchMe().catch(() => {}) // atualiza o nome mostrado no topo
  emit('update:modelValue', false)
  emit('saved')
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="isEdit ? 'Editar usuário' : 'Novo usuário'"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form id="user-form" novalidate autocomplete="off" class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">{{ formError }}</p>

      <BaseInput ref="firstField" v-model="form.name" label="Nome" required :error="errors.name" />
      <BaseInput
        v-model="form.email"
        label="E-mail"
        type="email"
        autocomplete="off"
        :required="!isEdit"
        :disabled="isEdit"
        :error="errors.email"
        :help="isEdit ? 'O e-mail não pode ser alterado.' : ''"
      />
      <BaseSelect
        v-model="form.role"
        label="Perfil"
        required
        :options="roleOptions"
        :disabled="isSelf"
        :error="errors.role"
        :help="isSelf ? 'Você não pode alterar o seu próprio perfil.' : ''"
      />

      <fieldset class="space-y-4 rounded-lg border border-slate-200 p-4">
        <legend class="px-1 text-sm font-medium text-slate-700">{{ isEdit ? 'Redefinir senha (opcional)' : 'Senha' }}</legend>
        <BaseInput
          v-model="form.password"
          :label="isEdit ? 'Nova senha' : 'Senha'"
          :type="showPasswords ? 'text' : 'password'"
          autocomplete="new-password"
          :required="!isEdit"
          :error="errors.password"
          :help="`Mínimo de ${PASSWORD_MIN} caracteres.`"
        />
        <BaseInput
          v-model="form.confirm"
          label="Confirmar senha"
          :type="showPasswords ? 'text' : 'password'"
          autocomplete="new-password"
          :required="!isEdit"
          :error="errors.confirm"
        />
        <label class="inline-flex items-center gap-2 text-sm text-slate-600">
          <input v-model="showPasswords" type="checkbox" class="size-4 rounded border-slate-300 text-emerald-600" />
          Mostrar senhas
        </label>
      </fieldset>
    </form>

    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="user-form" :loading="submitting">{{ isEdit ? 'Salvar alterações' : 'Cadastrar' }}</BaseButton>
    </template>
  </BaseModal>
</template>
