import http from './http'

export const login = (email, password) =>
  http.post('/auth/login', { email, password }).then((r) => r.data)
export const getMe = () => http.get('/auth/me').then((r) => r.data)
