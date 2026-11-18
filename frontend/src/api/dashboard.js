import http from './http'

export const getDashboard = () => http.get('/dashboard').then((r) => r.data)
