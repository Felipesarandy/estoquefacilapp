import { computed, ref } from 'vue'

export function usePagination(initialPerPage = 20) {
  const page = ref(1)
  const perPage = ref(initialPerPage)
  const total = ref(0)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))
  const params = computed(() => ({ page: page.value, per_page: perPage.value }))

  function setPage(p) {
    page.value = Math.min(Math.max(1, p), totalPages.value)
  }
  function reset() {
    page.value = 1
  }
  /** Atualiza o estado a partir da resposta paginada da API. */
  function applyResponse(data) {
    page.value = data.page
    perPage.value = data.per_page
    total.value = data.total
  }

  return { page, perPage, total, totalPages, params, setPage, reset, applyResponse }
}
