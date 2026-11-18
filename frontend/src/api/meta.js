import http from './http'

export const getMeta = () => http.get('/meta').then((r) => r.data)
