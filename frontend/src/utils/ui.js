// Classes Tailwind compartilhadas pelos campos de formulário.
export function fieldClasses(hasError) {
  return [
    'block w-full rounded-lg border bg-white px-3 py-2 text-slate-900 shadow-sm placeholder:text-slate-400',
    'focus:outline-2 focus:outline-offset-1 focus:outline-emerald-600',
    'disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500',
    hasError ? 'border-red-500' : 'border-slate-300',
  ]
}
