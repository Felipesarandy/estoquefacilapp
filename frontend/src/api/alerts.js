import http from './http'

export const listAlerts = (params) => http.get('/alerts', { params }).then((r) => r.data)
