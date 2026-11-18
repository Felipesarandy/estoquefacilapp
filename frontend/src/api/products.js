import http from './http'

export const listProducts = (params) => http.get('/products', { params }).then((r) => r.data)
export const getProduct = (id) => http.get(`/products/${id}`).then((r) => r.data)
export const createProduct = (payload) => http.post('/products', payload).then((r) => r.data)
export const updateProduct = (id, payload) => http.patch(`/products/${id}`, payload).then((r) => r.data)

/** Percorre todas as páginas (100 por vez) e devolve a lista completa de produtos. */
export async function listAllProducts(params = {}) {
  const all = []
  for (let page = 1; ; page++) {
    const res = await listProducts({ ...params, page, per_page: 100 })
    all.push(...res.items)
    if (!res.items.length || all.length >= res.total) return all
  }
}
