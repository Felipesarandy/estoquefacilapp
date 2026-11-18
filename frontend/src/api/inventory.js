import http from './http'

export const listInventory = (params) => http.get('/inventory', { params }).then((r) => r.data)
export const getInventoryCount = (id) => http.get(`/inventory/${id}`).then((r) => r.data)
export const createInventoryCount = (payload) => http.post('/inventory', payload).then((r) => r.data)
