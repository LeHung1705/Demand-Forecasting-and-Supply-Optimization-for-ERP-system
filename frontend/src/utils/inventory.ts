export type InventoryInputs = {
  leadTimeHours: number
  serviceLevel: 0.9 | 0.95 | 0.99
}

export type InventoryOutputs = {
  leadTimeDemandMean: number
  safetyStock: number
  rop: number
  suggestedOrder: number
}

function zForServiceLevel(level: number) {
  if (level >= 0.99) return 2.33
  if (level >= 0.95) return 1.65
  return 1.28
}

export function computeInventoryOutputs(inputs: InventoryInputs, meanPerHour: number): InventoryOutputs {
  const leadMean = meanPerHour * inputs.leadTimeHours
  const sd = 0.3 * meanPerHour
  const z = zForServiceLevel(inputs.serviceLevel)
  const safetyStock = Math.round(z * sd * Math.sqrt(inputs.leadTimeHours))
  const rop = Math.round(leadMean + safetyStock)
  const suggestedOrder = Math.max(0, Math.round(1.5 * leadMean - 10))
  return {
    leadTimeDemandMean: Math.round(leadMean),
    safetyStock,
    rop,
    suggestedOrder,
  }
}
