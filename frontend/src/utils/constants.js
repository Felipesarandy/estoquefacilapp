// Rótulos e classes Tailwind (completas, para o Tailwind detectar) dos domínios da API.

export const STOCK_LEVELS = {
  ruptura: { label: 'Ruptura', classes: 'bg-red-100 text-red-800 ring-red-600/20' },
  critico: { label: 'Crítico', classes: 'bg-orange-100 text-orange-800 ring-orange-600/20' },
  atencao: { label: 'Atenção', classes: 'bg-amber-100 text-amber-800 ring-amber-600/20' },
  ok: { label: 'Ok', classes: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20' },
}

export const INCIDENT_STATUS = {
  aberto: { label: 'Aberto', classes: 'bg-red-100 text-red-800 ring-red-600/20' },
  em_analise: { label: 'Em análise', classes: 'bg-amber-100 text-amber-800 ring-amber-600/20' },
  resolvido: { label: 'Resolvido', classes: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20' },
  fechado: { label: 'Fechado', classes: 'bg-slate-100 text-slate-700 ring-slate-500/20' },
}

export const INCIDENT_SEVERITY = {
  baixa: { label: 'Baixa', classes: 'bg-slate-100 text-slate-700 ring-slate-500/20' },
  media: { label: 'Média', classes: 'bg-amber-100 text-amber-800 ring-amber-600/20' },
  alta: { label: 'Alta', classes: 'bg-orange-100 text-orange-800 ring-orange-600/20' },
  critica: { label: 'Crítica', classes: 'bg-red-100 text-red-800 ring-red-600/20' },
}

export const INCIDENT_TYPES = {
  ruptura: 'Ruptura',
  divergencia_inventario: 'Divergência de inventário',
  avaria: 'Avaria',
  vencimento: 'Vencimento',
  furto: 'Furto',
  outro: 'Outro',
}

export const ROLES = {
  admin: { label: 'Administrador', classes: 'bg-indigo-100 text-indigo-800 ring-indigo-600/20' },
  tratador: { label: 'Tratador', classes: 'bg-sky-100 text-sky-800 ring-sky-600/20' },
}

export const MOVEMENT_TYPES = { entrada: 'Entrada', saida: 'Saída' }

export const MOVEMENT_REASONS = {
  compra: 'Compra',
  doacao: 'Doação',
  ajuste: 'Ajuste',
  abastecimento_alimentador: 'Abastecimento do alimentador',
  trato_manual: 'Trato manual',
  avaria: 'Avaria',
  vencimento: 'Vencimento',
  furto: 'Furto',
}

export const ENTRY_REASONS = ['compra', 'doacao', 'ajuste']
export const EXIT_REASONS = [
  'abastecimento_alimentador',
  'trato_manual',
  'avaria',
  'vencimento',
  'furto',
  'ajuste',
]

export const UNITS = ['kg', 'g', 'sc', 'l', 'ml', 'un']
