import http from './http'

export const listMovements = (params) => http.get('/movements', { params }).then((r) => r.data)
export const getMovement = (id) => http.get(`/movements/${id}`).then((r) => r.data)
export const createMovement = (payload) => http.post('/movements', payload).then((r) => r.data)
/** Resumo diário: params { date } ou { from, to }. */
export const getDailyMovements = (params) =>
  http.get('/movements/daily', { params }).then((r) => r.data)
