<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { createIncident } from '../../api/incidents'
import { useApiForm } from '../../composables/useApiForm'
import { useToastStore } from '../../stores/toast'
import { INCIDENT_SEVERITY, INCIDENT_TYPES } from '../../utils/constants'
import BaseButton from '../ui/BaseButton.vue'
import BaseModal from '../ui/BaseModal.vue'
import BaseSelect from '../ui/BaseSelect.vue'
import BaseTextarea from '../ui/BaseTextarea.vue'
import ProductSelect from './ProductSelect.vue'

const props = defineProps({
  modelValue: Boolean,
  products: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const toast = useToastStore()
const form = reactive({ product_id: '', type: '', severity: '', description: '' })
const { errors, formError, submitting, reset, submit } = useApiForm(form)
const firstField = ref(null)

const typeOptions = Object.entries(INCIDENT_TYPES).map(([value, label]) => ({ value, label }))
const severityOptions = Object.entries(INCIDENT_SEVERITY).map(([value, { label }]) => ({ value, label }))
const activeProducts = computed(() => props.products.filter((p) => p.active))

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    reset()
    Object.assign(form, { product_id: '', type: '', severity: '', description: '' })
    await nextTick()
    await nextTick()
    firstField.value?.focus()
  },
)

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.type) errors.type = 'Selecione o tipo.'
  if (!form.description.trim()) errors.description = 'Descreva o incidente.'
  else if (form.description.length > 5000) errors.description = 'A descrição deve ter até 5000 caracteres.'
  return Object.keys(errors).length === 0
}

async function onSubmit() {
  if (submitting.value || !validate()) return
  const ok = await submit(async () => {
    try {
      await createIncident({
        product_id: form.product_id ? Number(form.product_id) : null,
        type: form.type,
        severity: form.severity || null,
        description: form.description.trim(),
      })
    } catch (err) {
      // 409: já existe incidente ativo igual (mesmo produto e tipo).
      if (err.status === 0 || err.status >= 500 || err.status === 403) toast.error(err.message)
      throw err
    }
  })
  if (ok) {
    toast.success('Incidente aberto.')
    emit('update:modelValue', false)
    emit('saved')
  }
}
</script>

<template>
  <BaseModal :model-value="modelValue" title="Novo incidente" :close-on-backdrop="!submitting" @update:model-value="emit('update:modelValue', $event)">
    <form id="incident-form" novalidate class="space-y-4" @submit.prevent="onSubmit">
      <p v-if="formError" role="alert" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200">{{ formError }}</p>
      <BaseSelect ref="firstField" v-model="form.type" label="Tipo" required placeholder="Selecione…" :options="typeOptions" :error="errors.type" />
      <BaseSelect
        v-model="form.severity"
        label="Gravidade"
        placeholder="Padrão (média)"
        :options="severityOptions"
        :error="errors.severity"
        help="Ruptura é sempre crítica."
      />
      <ProductSelect v-model="form.product_id" :products="activeProducts" placeholder="Sem produto" :error="errors.product_id" />
      <BaseTextarea v-model="form.description" label="Descrição" required :rows="4" :error="errors.description" />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('update:modelValue', false)">Cancelar</BaseButton>
      <BaseButton type="submit" form="incident-form" :loading="submitting">Abrir incidente</BaseButton>
    </template>
  </BaseModal>
</template>
