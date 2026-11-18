<script setup>
import { nextTick, reactive, ref, watch } from 'vue'
import { createSupplier, updateSupplier } from '../../api/suppliers'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'

const props = defineProps({
  modelValue: Boolean,
  supplier: { type: Object, default: null }, // null = criar
})
const emit = defineEmits(['update:modelValue', 'saved'])

const toast = useToastStore()
const form = reactive({ name: '', phone: '', email: '' })
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const nameInput = ref(null)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    form.name = props.supplier?.name ?? ''
    form.phone = props.supplier?.phone ?? ''
    form.email = props.supplier?.email ?? ''
    await nextTick()
    await nextTick()
    nameInput.value?.focus()
  },
)

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  const name = form.name.trim()
  const phone = form.phone.trim()
  const email = form.email.trim()
  if (!name) errors.name = 'Informe o nome.'
  else if (name.length > 120) errors.name = 'O nome deve ter até 120 caracteres.'
  if (phone) {
    if (phone.length > 20) errors.phone = 'O telefone deve ter até 20 caracteres.'
    else if (!/^[\d\s()+-]+$/.test(phone) || phone.replace(/\D/g, '').length < 8) {
      errors.phone = 'Informe um telefone válido, com DDD. Ex.: (11) 91234-5678.'
    }
  }
  if (email) {
    if (email.length > 255) errors.email = 'O e-mail deve ter até 255 caracteres.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Informe um e-mail válido.'
  }
  return Object.keys(errors).length === 0
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  const editing = !!props.supplier
  const ok = await submit(async () => {
    try {
      const payload = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
      }
      if (editing) await updateSupplier(props.supplier.id, payload)
      else await createSupplier(payload)
    } catch (err) {
      if (err.status === 409) err.fields = { name: err.message } // duplicidade de nome
      if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  if (ok) {
    toast.success(editing ? 'Fornecedor atualizado.' : 'Fornecedor cadastrado.')
    emit('update:modelValue', false)
    emit('saved')
  }
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="supplier ? 'Editar fornecedor' : 'Novo fornecedor'"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form id="supplier-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">
        {{ formError }}
      </p>
      <BaseInput ref="nameInput" v-model="form.name" label="Nome" required :error="errors.name" />
      <BaseInput v-model="form.phone" label="Telefone" type="tel" autocomplete="off" :error="errors.phone" help="Opcional." />
      <BaseInput v-model="form.email" label="E-mail" type="email" autocomplete="off" :error="errors.email" help="Opcional." />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="supplier-form" :loading="submitting">
        {{ supplier ? 'Salvar alterações' : 'Cadastrar' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
