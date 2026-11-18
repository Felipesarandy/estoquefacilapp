import http from './http'

export const listAudit = (params) => http.get('/audit', { params }).then((r) => r.data)
export const getAuditEntry = (id) => http.get(`/audit/${id}`).then((r) => r.data)
