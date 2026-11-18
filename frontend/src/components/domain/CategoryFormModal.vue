<script setup>
import { nextTick, reactive, ref, watch } from 'vue'
import { createCategory, updateCategory } from '../../api/categories'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import BaseButton from '../ui/BaseButton.vue'
import BaseInput from '../ui/BaseInput.vue'
import BaseModal from '../ui/BaseModal.vue'

const props = defineProps({
  modelValue: Boolean,
  category: { type: Object, default: null }, // null = criar
})
const emit = defineEmits(['update:modelValue', 'saved'])

const toast = useToastStore()
const form = reactive({ name: '' })
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const nameInput = ref(null)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    form.name = props.category?.name ?? ''
    await nextTick()
    await nextTick()
    nameInput.value?.focus()
  },
)

function validate() {
  delete errors.name
  const name = form.name.trim()
  if (!name) errors.name = 'Informe o nome.'
  else if (name.length > 80) errors.name = 'O nome deve ter até 80 caracteres.'
  return !errors.name
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  const editing = !!props.category
  const ok = await submit(async () => {
    try {
      const payload = { name: form.name.trim() }
      if (editing) await updateCategory(props.category.id, payload)
      else await createCategory(payload)
    } catch (err) {
      if (err.status === 409) err.fields = { name: err.message } // duplicidade de nome
      if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  if (ok) {
    toast.success(editing ? 'Categoria atualizada.' : 'Categoria cadastrada.')
    emit('update:modelValue', false)
    emit('saved')
  }
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="category ? 'Editar categoria' : 'Nova categoria'"
    size="sm"
    :close-on-backdrop="!submitting"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <form id="category-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">
        {{ formError }}
      </p>
      <BaseInput ref="nameInput" v-model="form.name" label="Nome" required :error="errors.name" />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="category-form" :loading="submitting">
        {{ category ? 'Salvar alterações' : 'Cadastrar' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
