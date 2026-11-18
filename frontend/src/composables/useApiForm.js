import { reactive, ref, watch } from 'vue'

/**
 * Estado de formulário ligado à API.
 * - errors: mensagem por campo (vinda de ApiError.fields ou da validação no cliente)
 * - formError: erro geral (sem campo associado)
 * - Se `form` (reactive) for informado, editar um campo limpa o erro dele.
 */
export function useApiForm(form = null) {
  const errors = reactive({})
  const formError = ref('')
  const submitting = ref(false)

  function clearError(field) {
    delete errors[field]
  }

  function reset() {
    Object.keys(errors).forEach((k) => delete errors[k])
    formError.value = ''
    submitting.value = false
  }

  function setApiError(err) {
    const fields = err?.fields ?? {}
    Object.assign(errors, fields)
    if (!Object.keys(fields).length) formError.value = err?.message ?? 'Erro inesperado.'
  }

  /** Executa `fn` controlando `submitting`; devolve true se deu certo. */
  async function submit(fn) {
    formError.value = ''
    submitting.value = true
    try {
      await fn()
      return true
    } catch (err) {
      setApiError(err)
      return false
    } finally {
      submitting.value = false
    }
  }

  if (form) {
    watch(
      () => ({ ...form }),
      (novo, antigo) => {
        for (const key of Object.keys(novo)) {
          if (novo[key] !== antigo?.[key]) clearError(key)
        }
      },
    )
  }

  return { errors, formError, submitting, clearError, reset, setApiError, submit }
}
