// Exportação de CSV no navegador (sem dependências), pensada para abrir no Excel em português.

const SEPARATOR = ';'

/** Número com vírgula decimal e sem separador de milhar. */
export function csvNumber(value) {
  return Number(value).toLocaleString('pt-BR', { useGrouping: false, maximumFractionDigits: 3 })
}

function escapeCell(cell) {
  const text = String(cell ?? '')
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/** rows: array de arrays (a primeira linha é o cabeçalho). */
export function buildCsv(rows) {
  return rows.map((row) => row.map(escapeCell).join(SEPARATOR)).join('\r\n')
}

/** Baixa o CSV com BOM UTF-8 (o Excel reconhece os acentos). */
export function downloadCsv(filename, rows) {
  const blob = new Blob(['﻿', buildCsv(rows)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
