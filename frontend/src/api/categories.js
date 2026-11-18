import http from './http'

export const listCategories = (params) => http.get('/categories', { params }).then((r) => r.data)
export const getCategory = (id) => http.get(`/categories/${id}`).then((r) => r.data)
export const createCategory = (payload) => http.post('/categories', payload).then((r) => r.data)
export const updateCategory = (id, payload) => http.patch(`/categories/${id}`, payload).then((r) => r.data)
