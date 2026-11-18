import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Listagem paginada com busca (debounce de 300 ms) sincronizada com a URL (?q=&page=).
 * `fetcher(params)` recebe { search, page, per_page } e devolve { items, total }.
 */
export function useCrudList(fetcher, { routeName, perPage = 10 } = {}) {
  const route = useRoute()
  const router = useRouter()

  const q = computed(() => String(route.query.q ?? ''))
  const page = computed(() => Math.max(1, parseInt(route.query.page) || 1))

  const rows = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  let requestId = 0

  function setQuery(patch, { replace = false, keepPage = false } = {}) {
    const next = { ...route.query, ...patch }
    if (!keepPage) delete next.page
    for (const key of Object.keys(next)) {
      if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
    }
    if (next.page === 1) delete next.page
    return router[replace ? 'replace' : 'push']({ query: next })
  }

  async function load() {
    const id = ++requestId // descarta respostas antigas
    loading.value = true
    error.value = ''
    try {
      const res = await fetcher({ search: q.value || undefined, page: page.value, per_page: perPage })
      if (id !== requestId) return
      rows.value = res.items
      total.value = res.total
      if (!res.items.length && res.total > 0 && page.value > 1) {
        setQuery({ page: Math.ceil(res.total / perPage) }, { replace: true, keepPage: true })
      }
    } catch (err) {
      if (id !== requestId) return
      error.value = err.message
    } finally {
      if (id === requestId) loading.value = false
    }
  }

  const search = ref(q.value)
  let debounceId = null
  watch(search, (value) => {
    clearTimeout(debounceId)
    debounceId = setTimeout(() => {
      if (value.trim() !== q.value) setQuery({ q: value.trim() }, { replace: true })
    }, 300)
  })
  watch(q, (value) => {
    if (value !== search.value.trim()) search.value = value // voltar/avançar no navegador
  })

  watch(
    () => route.query,
    () => {
      if (!routeName || route.name === routeName) load()
    },
  )
  onMounted(load)

  const setPage = (p) => setQuery({ page: p }, { keepPage: true })
  function clearSearch() {
    clearTimeout(debounceId)
    search.value = ''
    router.push({ query: {} })
  }

  return { search, q, page, perPage, rows, total, loading, error, load, setPage, clearSearch }
}
