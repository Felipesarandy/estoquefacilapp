import { ref } from 'vue'

/** Estado independente (dados, carregando, erro) de um bloco carregado de uma função assíncrona. */
export function useAsyncBlock(loader) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function load() {
    loading.value = true
    error.value = ''
    try {
      data.value = await loader()
    } catch (err) {
      error.value = err?.message ?? 'Erro inesperado.'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, load }
}
