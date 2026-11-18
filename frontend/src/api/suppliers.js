import http from './http'

export const listSuppliers = (params) => http.get('/suppliers', { params }).then((r) => r.data)
export const getSupplier = (id) => http.get(`/suppliers/${id}`).then((r) => r.data)
export const createSupplier = (payload) => http.post('/suppliers', payload).then((r) => r.data)
export const updateSupplier = (id, payload) => http.patch(`/suppliers/${id}`, payload).then((r) => r.data)
