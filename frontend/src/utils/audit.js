import { formatDate, formatDateTime } from './format'

const SENSITIVE = /password|senha|hash/i
export const MASK = '••••••'

/** Copia o valor ocultando qualquer campo de senha/hash (mesmo aninhado). */
export function maskSensitive(value) {
  if (Array.isArray(value)) return value.map(maskSensitive)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, SENSITIVE.test(k) && k !== 'password_changed' ? MASK : maskSensitive(v)]),
    )
  }
  return value
}

/**
 * Valor legível: nulo -> "—", booleano -> Sim/Não, datas ISO formatadas.
 * Os snapshots guardam datas em UTC sem offset (ver API.md): trata como UTC.
 */
export function formatAuditValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'string') {
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return formatDate(value)
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) {
      return formatDateTime(/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`)
    }
  }
  return String(value)
}

/** Compara antes x depois e devolve uma linha por campo, com o tipo de mudança. */
export function diffSnapshots(before, after) {
  const b = maskSensitive(before) ?? {}
  const a = maskSensitive(after) ?? {}
  const keys = [...new Set([...Object.keys(a), ...Object.keys(b)])]
  return keys.map((key) => {
    const hasBefore = key in b
    const hasAfter = key in a
    let change = 'same'
    if (hasBefore && !hasAfter) change = 'removed'
    else if (!hasBefore && hasAfter) change = 'added'
    else if (JSON.stringify(b[key]) !== JSON.stringify(a[key])) change = 'changed'
    return { key, before: b[key], after: a[key], hasBefore, hasAfter, change }
  })
}
