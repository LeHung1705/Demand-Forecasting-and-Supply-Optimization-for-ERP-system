import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { loadDashboardFromApi, loadAccuracyFromApi } from '../services/dashboardApi'
import { computeKpisFromData, type ChartPoint } from '../utils/mockDashboardData'
import { computeInventoryOutputs, type InventoryInputs, type InventoryOutputs } from '../utils/inventory'
import { APP_CONFIG } from '../utils/constants'

// ✅ remove unused type alias to satisfy eslint
// type DashboardResult = Awaited<ReturnType<typeof loadDashboardFromApi>>

export type DashboardKpis = {
  observedSum: number
  stockoutHours: number
  recoveredSum: number
  forecastNextHorizon: number
}

type State = {
  timeRange: '7d' | '30d' | '90d'
  setTimeRange: (v: any) => void
  aggregation: 'hourly' | 'daily'
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

  accuracyInfo: any

  metaData: any
  setMetaData: (v: any) => void
}

const DashboardContext = React.createContext<State | undefined>(undefined)

function toNullableInt(v: string | undefined): number | null {
  const s = (v ?? '').trim()
  if (!s || s.toLowerCase() === 'all') return null
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}

function toEpochMs(s: any): number | null {
  const t = Date.parse(String(s))
  return Number.isFinite(t) ? t : null
}

function makeMockForecast(opts: {
  history: ChartPoint[]
  aggregation: 'hourly' | 'daily'
  horizonDays?: number
}): {
  historyBridged: ChartPoint[]
  forecast: ChartPoint[]
  lastHistory: { iso: string; ts: number; year: number; month: number; day: number }
} {
  const horizonDays = opts.horizonDays ?? 7
  const hist = (opts.history || [])
    .map((p) => ({ ...p, isForecast: false }))
    .filter((p) => toEpochMs(p.time) !== null)
    .sort((a, b) => (toEpochMs(a.time)! - toEpochMs(b.time)!))

  if (hist.length === 0) {
    return {
      historyBridged: hist,
      forecast: [],
      lastHistory: { iso: '', ts: 0, year: 0, month: 0, day: 0 },
    }
  }

  const last = hist[hist.length - 1]             // ✅ đây chính là điểm lịch sử gần nhất (last_dt)
  const lastTs = toEpochMs(last.time)!           // ✅ timestamp của last_dt

  // ✅ Trích xuất ngày/tháng/năm của last_dt để sau truyền cho AI
  const lastDate = new Date(lastTs)
  const lastHistory = {
    iso: new Date(lastTs).toISOString(),
    ts: lastTs,
    year: lastDate.getFullYear(),
    month: lastDate.getMonth() + 1, // 1-12
    day: lastDate.getDate(),        // 1-31
  }

  const stepMs = opts.aggregation === 'hourly' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000
  const steps = opts.aggregation === 'hourly' ? horizonDays * 24 : horizonDays

  const lastObserved = Number(last.observed ?? 0) || 0

  const historyBridged = hist.slice(0, -1).concat([
    {
      ...last,
      forecastMean: lastObserved,
      ciLower: null,
      ciUpper: null,
      isForecast: false,
    },
  ])

  const forecast: ChartPoint[] = []
  const base = Math.max(0, lastObserved)

  for (let i = 1; i <= steps; i++) {
    const ts = lastTs + i * stepMs
    const mean = Math.max(0, Math.round(base * (0.95 + 0.1 * Math.sin(i / 3)) + (Math.random() - 0.5) * 2))
    const band = Math.max(1, Math.round(mean * 0.2))

    forecast.push({
      time: new Date(ts).toISOString(),
      observed: null,
      recovered: null,
      forecastMean: mean,
      ciLower: Math.max(0, mean - band),
      ciUpper: mean + band,
      stockout: false,
      isForecast: true,
    })
  }

  return { historyBridged, forecast, lastHistory }
}

function mergeSorted(points: ChartPoint[]): ChartPoint[] {
  return (points || [])
    .filter((p) => toEpochMs(p.time) !== null)
    .slice()
    .sort((a, b) => (toEpochMs(a.time)! - toEpochMs(b.time)!))
}

function useInternalState(): State {
  const [timeRange, setTimeRange] = React.useState<'7d' | '30d' | '90d'>('30d')
  const [aggregation, setAggregation] = React.useState<'hourly' | 'daily'>('hourly')
  const [storeId, setStoreId] = React.useState<string>('all')
  const [sku, setSku] = React.useState<string>('')

  const [showStockout, setShowStockout] = React.useState<boolean>(true)
  const [showRecovered, setShowRecovered] = React.useState<boolean>(true)
  const [showForecastCI, setShowForecastCI] = React.useState<boolean>(true)

  // ✅ giữ riêng history / forecast
  const [historyData, setHistoryData] = React.useState<ChartPoint[]>([])
  const [forecastData, setForecastData] = React.useState<ChartPoint[]>([])

  const [chartData, setChartData] = React.useState<ChartPoint[]>([])
  const [kpis, setKpis] = React.useState<Partial<DashboardKpis>>({})

  const [inventoryInputs, setInventoryInputs] = React.useState<InventoryInputs>({
    leadTimeHours: 24,
    serviceLevel: 0.95,
  })
  const [inventoryOutputs, setInventoryOutputs] = React.useState<InventoryOutputs>({
    leadTimeDemandMean: 0,
    safetyStock: 0,
    rop: 0,
    suggestedOrder: 0,
  })

  const [loading, setLoading] = React.useState(false)
  const [replenishmentOpen, setReplenishmentOpen] = React.useState(false)

  const [accuracyInfo, setAccuracyInfo] = React.useState<any>(null)

  const [metaData, setMetaData] = useState<any>(null)

  const mergedAll = useMemo(() => mergeSorted([...historyData, ...forecastData]), [historyData, forecastData])

  // ✅ OFF => chỉ history (no empty tail). ON => history + forecast (sorted)
  useEffect(() => {
    setChartData(showForecastCI ? mergedAll : mergeSorted(historyData))
  }, [showForecastCI, mergedAll, historyData])

  // ✅ KPI tính trên mergedAll để KPI forecast không bị mất khi toggle OFF
  useEffect(() => {
    setKpis(computeKpisFromData(mergedAll))
  }, [mergedAll])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const base = APP_CONFIG.API_URL || 'http://localhost:8000'

      const sid = toNullableInt(storeId)
      const pid = toNullableInt(sku)

      const params = new URLSearchParams({
        time_range: timeRange,
        aggregation: aggregation, // giữ theo state; backend có thể chỉ hỗ trợ daily
      })
      if (sid !== null) params.set('store_id', String(sid))
      if (pid !== null) params.set('product_id', String(pid))

      const res = await fetch(`${base}/api/v1/dashboard/series?${params.toString()}`)
      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(`dashboard/series failed (${res.status}): ${txt}`)
      }

      const json = await res.json()
      setMetaData(json?.meta ?? null)

      // Build history only from observed+recovered (no forecast from backend)
      const byDt = new Map<string, ChartPoint>()

      for (const p of json?.observed || []) {
        const dt = String(p.dt)
        byDt.set(dt, {
          time: dt,
          observed: Number(p.value) || 0,
          recovered: null,
          forecastMean: null,
          ciLower: null,
          ciUpper: null,
          stockout: false,
          isForecast: false,
        })
      }

      for (const p of json?.recovered || []) {
        const dt = String(p.dt)
        const cur = byDt.get(dt)
        if (cur) {
          cur.recovered = Number(p.value) || 0
        } else {
          byDt.set(dt, {
            time: dt,
            observed: null,
            recovered: Number(p.value) || 0,
            forecastMean: null,
            ciLower: null,
            ciUpper: null,
            stockout: false,
            isForecast: false,
          })
        }
      }

      const history = Array.from(byDt.values())
        .filter((x) => toEpochMs(x.time) !== null)
        .sort((a, b) => (toEpochMs(a.time)! - toEpochMs(b.time)!))

      setHistoryData(history)

      // ✅ Make mock forecast AFTER last history point, with bridge
      const { historyBridged, forecast, lastHistory } = makeMockForecast({
        history,
        aggregation,
        horizonDays: 7,
      })

      setHistoryData(historyBridged)
      setForecastData(forecast)

      // ✅ expose last_dt parts cho AI (không phá meta từ backend)
      setMetaData((prev: any) => ({
        ...(prev && typeof prev === 'object' ? prev : {}),
        last_history: lastHistory,
      }))

      // Accuracy panel (nếu còn dùng ở nơi khác)
      if (pid !== null) {
        const acc = await loadAccuracyFromApi({ timeRange, aggregation, storeId, sku })
        setAccuracyInfo(acc)
      } else {
        setAccuracyInfo(null)
      }

      // Inventory suggestion dựa trên KPI (mergedAll sẽ cập nhật qua effect)
      const nextKpis = computeKpisFromData(mergeSorted([...historyBridged, ...forecast]))
      const histOnly = historyBridged
      const daysOrHours = Math.max(1, histOnly.length)
      const denom = aggregation === 'hourly' ? daysOrHours : (daysOrHours * 24)
      const meanPerHour = Math.max(1, Math.round((nextKpis.observedSum || 0) / denom))
      setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerHour))
    } finally {
      setLoading(false)
    }
  }, [aggregation, inventoryInputs, sku, storeId, timeRange])

  const runRecoveryAndForecast = React.useCallback(() => {
    // giữ nguyên chức năng cũ nếu có nơi gọi; không làm forecast quá khứ
    setHistoryData((prev) =>
      prev.map((p) => {
        if (p.isForecast) return p
        const recovered = p.recovered ?? Math.round((p.observed ?? 0) * (1 + Math.random() * 0.3))
        return { ...p, recovered }
      })
    )
  }, [])

  React.useEffect(() => {
    const meanPerHour = Math.max(1, Math.round((kpis.observedSum ?? 0) / Math.max(1, chartData.length)))
    setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerHour))
  }, [inventoryInputs, chartData, kpis])

  return {
    timeRange,
    setTimeRange,
    aggregation,
    setAggregation,
    storeId,
    setStoreId,
    sku,
    setSku,
    showStockout,
    setShowStockout,
    showRecovered,
    setShowRecovered,
    showForecastCI,
    setShowForecastCI,
    chartData,
    setChartData,
    kpis,
    setKpis,
    inventoryInputs,
    setInventoryInputs,
    inventoryOutputs,
    setInventoryOutputs,
    loadData,
    runRecoveryAndForecast,
    loading,
    replenishmentOpen,
    setReplenishmentOpen,
    accuracyInfo,
    metaData,
    setMetaData,
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