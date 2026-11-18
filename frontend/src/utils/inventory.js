import { formatDecimal } from './format'

/** Diferença (contado - sistema) com 3 casas, sem erro de ponto flutuante visível. */
export function countDifference(counted, system) {
  return Number((Number(counted) - Number(system)).toFixed(3))
}

/** "+2,5" / "-2" / "0" */
export function signedDecimal(value) {
  const n = Number(value)
  return `${n > 0 ? '+' : ''}${formatDecimal(n)}`
}

/** Classe de cor: zero slate, sobra amber, falta rose. */
export function differenceClass(value) {
  const n = Number(value)
  return n > 0 ? 'text-amber-700' : n < 0 ? 'text-rose-700' : 'text-slate-600'
}
