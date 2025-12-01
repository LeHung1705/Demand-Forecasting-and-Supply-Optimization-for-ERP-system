import React from 'react'
import { ChartPoint, generateMockData, computeKpisFromData } from '../utils/mockDashboardData'
import { InventoryInputs, InventoryOutputs, computeInventoryOutputs } from '../utils/inventory'

export type DashboardKpis = {
  observedSum: number
  stockoutHours: number
  recoveredSum: number
  forecastNextHorizon: number
}

type State = {
  timeRange: '7d'|'30d'|'90d'
  setTimeRange: (v: any) => void
  aggregation: 'hourly'|'daily'
  setAggregation: (v: any) => void
  storeId: string
  setStoreId: (v: any) => void
  sku: string
  setSku: (v: any) => void
  showStockout: boolean
  setShowStockout: (v: any) => void
  showRecovered: boolean
  setShowRecovered: (v: any) => void
  showForecastCI: boolean
  setShowForecastCI: (v: any) => void
  chartData: ChartPoint[]
  setChartData: (d: ChartPoint[]) => void
  kpis: Partial<DashboardKpis>
  setKpis: (k: Partial<DashboardKpis>) => void
  inventoryInputs: InventoryInputs
  setInventoryInputs: (i: InventoryInputs) => void
  inventoryOutputs: InventoryOutputs
  setInventoryOutputs: (o: InventoryOutputs) => void
  loadData: () => Promise<void>
  runRecoveryAndForecast: () => void
  loading: boolean
  replenishmentOpen: boolean
  setReplenishmentOpen: (v: boolean) => void
}

const DashboardContext = React.createContext<State | undefined>(undefined)

function useInternalState(): State {
  const [timeRange, setTimeRange] = React.useState<'7d'|'30d'|'90d'>('7d')
  const [aggregation, setAggregation] = React.useState<'hourly'|'daily'>('hourly')
  const [storeId, setStoreId] = React.useState<string>('all')
  const [sku, setSku] = React.useState<string>('')

  const [showStockout, setShowStockout] = React.useState<boolean>(true)
  const [showRecovered, setShowRecovered] = React.useState<boolean>(true)
  const [showForecastCI, setShowForecastCI] = React.useState<boolean>(true)

  const [chartData, setChartData] = React.useState<ChartPoint[]>([])
  const [kpis, setKpis] = React.useState<Partial<DashboardKpis>>({})

  const [inventoryInputs, setInventoryInputs] = React.useState<InventoryInputs>({ leadTimeHours: 24, serviceLevel: 0.95 })
  const [inventoryOutputs, setInventoryOutputs] = React.useState<InventoryOutputs>({ leadTimeDemandMean:0, safetyStock:0, rop:0, suggestedOrder:0 })

  const [loading, setLoading] = React.useState(false)
  const [replenishmentOpen, setReplenishmentOpen] = React.useState(false)

  const loadData = React.useCallback(async () => {
    setLoading(true)
    const { loadMockDashboard } = await import('../services/dashboardApi')
    const res = await loadMockDashboard()
    setChartData(res.data)
    setKpis(res.kpis)
    const meanPerHour = Math.max(1, Math.round((res.kpis.observedSum ?? 0) / Math.max(1, (res.data.length))))
    const invOut = computeInventoryOutputs(inventoryInputs, meanPerHour)
    setInventoryOutputs(invOut)
    setLoading(false)
  }, [inventoryInputs])

  const runRecoveryAndForecast = React.useCallback(() => {
    setChartData(prev => prev.map((p) => {
      if (p.forecastMean !== undefined) return p
      const recovered = p.recovered ?? Math.round((p.observed ?? 0) * (1 + Math.random() * 0.3))
      const forecastMean = Math.round((recovered ?? p.observed ?? 0) * (1 + 0.1 * Math.random()))
      return { ...p, recovered, forecastMean, ciLower: Math.max(0, forecastMean - 4), ciUpper: forecastMean + 4 }
    }))
    // KPIs will update via effect below
  }, [])

  React.useEffect(() => {
    // recompute KPIs from chartData
    setKpis(computeKpisFromData(chartData))
  }, [chartData])

  React.useEffect(() => {
    const meanPerHour = Math.max(1, Math.round((kpis.observedSum ?? 0) / Math.max(1, (chartData.length))))
    setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerHour))
  }, [inventoryInputs, chartData, kpis])

  return {
    timeRange, setTimeRange,
    aggregation, setAggregation,
    storeId, setStoreId,
    sku, setSku,
    showStockout, setShowStockout,
    showRecovered, setShowRecovered,
    showForecastCI, setShowForecastCI,
    chartData, setChartData,
    kpis, setKpis,
    inventoryInputs, setInventoryInputs,
    inventoryOutputs, setInventoryOutputs,
    loadData,
    runRecoveryAndForecast,
    loading,
    replenishmentOpen, setReplenishmentOpen,
  }
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const state = useInternalState()
  return <DashboardContext.Provider value={state}>{children}</DashboardContext.Provider>
}

export function useDashboardState() {
  const ctx = React.useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboardState must be used within DashboardProvider')
  return ctx
}

