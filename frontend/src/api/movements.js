import http from './http'

export const listMovements = (params) => http.get('/movements', { params }).then((r) => r.data)
export const getMovement = (id) => http.get(`/movements/${id}`).then((r) => r.data)
export const createMovement = (payload) => http.post('/movements', payload).then((r) => r.data)
/** Resumo diário: params { date } ou { from, to }. */
export const getDailyMovements = (params) =>
  http.get('/movements/daily', { params }).then((r) => r.data)

/** Percorre todas as páginas (100 por vez) das movimentações que atendem aos filtros. */
export async function listAllMovements(params = {}) {
  const all = []
  for (let page = 1; ; page++) {
    const res = await listMovements({ ...params, page, per_page: 100 })
    all.push(...res.items)
    if (!res.items.length || all.length >= res.total) return all
  }
}
