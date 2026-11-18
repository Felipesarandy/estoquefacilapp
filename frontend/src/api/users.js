import http from './http'

export const listUsers = (params) => http.get('/users', { params }).then((r) => r.data)
export const getUser = (id) => http.get(`/users/${id}`).then((r) => r.data)
export const createUser = (payload) => http.post('/users', payload).then((r) => r.data)
export const updateUser = (id, payload) => http.patch(`/users/${id}`, payload).then((r) => r.data)
