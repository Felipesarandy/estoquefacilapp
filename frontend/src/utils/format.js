const TZ = 'America/Sao_Paulo'

/** "85.000" -> "85"; "3.333" -> "3,333". Sem zeros à toa, em pt-BR. */
export function formatDecimal(value, maxDigits = 3) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: maxDigits })
}

export function formatQuantity(value, unit) {
  const text = formatDecimal(value, 3)
  return unit && text !== '—' ? `${text} ${unit}` : text
}

/** Valor monetário (ex.: "5.80" -> "R$ 5,80"). */
export function formatCurrency(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// Datas só com dia ("2026-11-27") são tratadas ao meio-dia para não recuar de dia no fuso.
function toDate(iso) {
  if (!iso) return null
  const date = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T12:00:00`) : new Date(iso)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(iso) {
  const date = toDate(iso)
  if (!date) return '—'
  return date.toLocaleDateString('pt-BR', { timeZone: TZ })
}

export function formatDateTime(iso) {
  const date = toDate(iso)
  if (!date) return '—'
  return date.toLocaleString('pt-BR', {
    timeZone: TZ,
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

/** Data de hoje (YYYY-MM-DD) no fuso America/Sao_Paulo. */
export function todayISO() {
  return new Date().toLocaleDateString('sv-SE', { timeZone: TZ })
}

/** Soma dias a uma data YYYY-MM-DD (negativo subtrai). */
export function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** "2026-11-17" -> "17/11" */
export function formatDayMonth(iso) {
  const [, month, day] = iso.split('-')
  return `${day}/${month}`
}

/** Hora (HH:mm) no fuso America/Sao_Paulo. */
export function formatTime(date = new Date()) {
  return date.toLocaleTimeString('pt-BR', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
}

/** "2026-11-17" -> "17/11/2026 (ter)" (dia da semana abreviado). */
export function formatDateWeekday(iso) {
  const date = toDate(iso)
  if (!date) return '—'
  const weekday = date.toLocaleDateString('pt-BR', { timeZone: TZ, weekday: 'short' }).replace('.', '')
  return `${formatDate(iso)} (${weekday})`
}

/** Dias entre duas datas YYYY-MM-DD, inclusive as duas pontas. */
export function daysBetween(fromIso, toIso) {
  return Math.round((new Date(`${toIso}T00:00:00Z`) - new Date(`${fromIso}T00:00:00Z`)) / 86400000) + 1
}
