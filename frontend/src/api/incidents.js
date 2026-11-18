import http from './http'

export const listIncidents = (params) => http.get('/incidents', { params }).then((r) => r.data)
export const getIncidentsSummary = () => http.get('/incidents/summary').then((r) => r.data)
export const getIncident = (id) => http.get(`/incidents/${id}`).then((r) => r.data)
export const createIncident = (payload) => http.post('/incidents', payload).then((r) => r.data)
export const updateIncident = (id, payload) =>
  http.patch(`/incidents/${id}`, payload).then((r) => r.data)
