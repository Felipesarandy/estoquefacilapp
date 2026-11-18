import http from './http'

export const listProducts = (params) => http.get('/products', { params }).then((r) => r.data)
export const getProduct = (id) => http.get(`/products/${id}`).then((r) => r.data)
export const createProduct = (payload) => http.post('/products', payload).then((r) => r.data)
export const updateProduct = (id, payload) => http.patch(`/products/${id}`, payload).then((r) => r.data)
