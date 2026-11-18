/**
 * Nível previsto de um produto depois de uma movimentação (mesma regra do backend):
 * saldo <= 0 -> ruptura; saldo <= colchão mínimo -> crítico;
 * cobertura (saldo / consumo diário) <= dias de antecedência -> atenção; senão ok.
 */
export function predictLevel(stockAfter, minStock, dailyConsumption, daysAhead = 5) {
  const stock = Number(stockAfter)
  if (stock <= 0) return 'ruptura'
  if (stock <= Number(minStock)) return 'critico'
  const daily = Number(dailyConsumption)
  if (daily > 0 && stock / daily <= daysAhead) return 'atencao'
  return 'ok'
}
