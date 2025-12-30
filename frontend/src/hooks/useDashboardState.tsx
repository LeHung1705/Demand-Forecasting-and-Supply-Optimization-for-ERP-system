import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { computeKpisFromData, type ChartPoint } from '../utils/mockDashboardData'
import { computeInventoryOutputs, type InventoryInputs, type InventoryOutputs } from '../utils/inventory'
import { APP_CONFIG } from '../utils/constants'
import { fetchInventoryPlan } from '../services/inventoryService'
import { loadAccuracyFromApi } from '../services/dashboardApi'

export type DashboardKpis = {
  observedSum: number
  stockoutHours: number
  recoveredSum: number
  forecastNextHorizon: number
}

export type DashboardState = {
  timeRange: '7d' | '30d' | '90d'
  setTimeRange: (v: '7d' | '30d' | '90d') => void

  aggregation: 'hourly' | 'daily'
  setAggregation: (v: 'hourly' | 'daily') => void

  storeId: string
  setStoreId: (v: string) => void

  sku: string
  setSku: (v: string) => void

  showStockout: boolean
  setShowStockout: (v: boolean) => void

  showRecovered: boolean
  setShowRecovered: (v: boolean) => void

  showForecastCI: boolean
  setShowForecastCI: (v: boolean) => void

  chartData: ChartPoint[]
  kpis: Partial<DashboardKpis>

  inventoryInputs: InventoryInputs
  setInventoryInputs: (v: InventoryInputs) => void

  inventoryOutputs: InventoryOutputs
  replenishmentOpen: boolean
  setReplenishmentOpen: (v: boolean) => void

  loadData: () => Promise<void>
  loading: boolean

  accuracyInfo: any
  metaData: any
}

const DashboardContext = React.createContext<DashboardState | null>(null)

function toEpochMs(v: string): number | null {
  const t = Date.parse(v)
  return Number.isFinite(t) ? t : null
}

function mergeSorted(points: ChartPoint[]): ChartPoint[] {
  return (points || [])
    .filter((p) => toEpochMs(p.time) !== null)
    .slice()
    .sort((a, b) => (toEpochMs(a.time)! - toEpochMs(b.time)!))
}

function toNullableInt(v?: string): number | null {
  const s = String(v ?? '').trim()
  // null means "all"
  if (!s || s.toLowerCase() === 'all') return null

  const n = Number(s)
  if (!Number.isFinite(n)) return null

  // ✅ allow 0 (store_id/product_id can legitimately be 0)
  const i = Math.trunc(n)
  return i >= 0 ? i : null
}

function deriveLastHistory(meta: any): { year: number; month: number; day: number } | null {
  const raw = meta?.max_dt || meta?.to_date
  if (!raw) return null
  const d = new Date(String(raw))
  if (Number.isNaN(d.getTime())) return null
  return { year: d.getFullYear(), month: d.getMonth() + 1, day: d.getDate() }
}

function useInternalState(): DashboardState {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [aggregation, setAggregation] = useState<'hourly' | 'daily'>('daily')
  const [storeId, setStoreId] = useState<string>('all')
  const [sku, setSku] = useState<string>('')

  const [showStockout, setShowStockout] = useState<boolean>(true)
  const [showRecovered, setShowRecovered] = useState<boolean>(true)
  const [showForecastCI, setShowForecastCI] = useState<boolean>(true)

  const [historyData, setHistoryData] = useState<ChartPoint[]>([])
  const [forecastData, setForecastData] = useState<ChartPoint[]>([])

  const [kpis, setKpis] = useState<Partial<DashboardKpis>>({})

  const [inventoryInputs, setInventoryInputs] = useState<InventoryInputs>({
    leadTimeHours: 24,
    serviceLevel: 0.95,
  })

  const [inventoryOutputs, setInventoryOutputs] = useState<InventoryOutputs>({
    leadTimeDemandMean: 0,
    safetyStock: 0,
    rop: 0,
    suggestedOrder: 0,
  })

  const [loading, setLoading] = useState(false)
  const [replenishmentOpen, setReplenishmentOpen] = useState(false)
  const [accuracyInfo, setAccuracyInfo] = useState<any>(null)
  const [metaData, setMetaData] = useState<any>(null)

  const mergedAll = useMemo(() => mergeSorted([...historyData, ...forecastData]), [historyData, forecastData])

  const chartData = useMemo(() => {
    // Nếu user tắt forecast => chỉ show lịch sử
    return showForecastCI ? mergedAll : mergeSorted(historyData)
  }, [showForecastCI, mergedAll, historyData])

  // KPI dựa trên chartData (đã apply showForecastCI)
  useEffect(() => {
    setKpis(computeKpisFromData(chartData))
  }, [chartData])

  const refreshInventoryFromApi = useCallback(async () => {
    const sid = toNullableInt(storeId)
    const pid = toNullableInt(sku)

    // Nếu chưa chọn SKU => fallback mock (tránh gọi API "all products" nặng)
    if (!pid) {
      const denom = Math.max(1, chartData.length)
      const meanPerPoint = Math.max(1, Math.round((kpis.observedSum ?? 0) / denom))
      setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerPoint))
      return
    }

    try {
      const res = await fetchInventoryPlan({
        time_range: timeRange,
        store_id: sid,
        product_id: pid,
        lead_time_hours: Number(inventoryInputs.leadTimeHours),
        service_level: Number(inventoryInputs.serviceLevel),
      })

      const m = res.metrics
      setInventoryOutputs({
        leadTimeDemandMean: Math.round(Number(m.lead_time_demand || 0)),
        safetyStock: Math.round(Number(m.safety_stock || 0)),
        rop: Math.round(Number(m.reorder_point || 0)),
        suggestedOrder: Math.round(Number(m.suggested_order_qty ?? m.reorder_point ?? 0)),
      })
    } catch {
      // Fallback mock nếu API lỗi
      const denom = Math.max(1, chartData.length)
      const meanPerPoint = Math.max(1, Math.round((kpis.observedSum ?? 0) / denom))
      setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerPoint))
    }
  }, [storeId, sku, timeRange, inventoryInputs, chartData.length, kpis.observedSum])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const base = APP_CONFIG.API_URL || 'http://localhost:8000'
      const sid = toNullableInt(storeId)
      const pid = toNullableInt(sku)

      const params = new URLSearchParams({
        time_range: timeRange,
        aggregation: aggregation,
      })
      if (sid !== null) params.set('store_id', String(sid))
      if (pid !== null) params.set('product_id', String(pid))

      const url = `${base}/api/v1/dashboard/series?${params.toString()}`
      const res = await fetch(url)
      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(`Load dashboard failed (${res.status}): ${txt}`)
      }
      const json = await res.json()

      const meta = json?.meta || {}
      setMetaData({
        ...meta,
        last_history: deriveLastHistory(meta),
      })

      const observed: Array<{ dt: string; value: number }> = Array.isArray(json?.observed) ? json.observed : []
      const recovered: Array<{ dt: string; value: number }> = Array.isArray(json?.recovered) ? json.recovered : []
      const forecast: Array<{ dt: string; value: number }> = Array.isArray(json?.forecast) ? json.forecast : []

      const byTime = new Map<string, ChartPoint>()
      const forecastTimes = new Set<string>()

      for (const p of observed) {
        const t = String(p.dt)
        const cur = byTime.get(t) ?? {
          time: t,
          observed: null,
          recovered: null,
          forecastMean: null,
          ciLower: null,
          ciUpper: null,
          stockout: false,
          isForecast: false,
        }
        cur.observed = Number(p.value) || 0
        byTime.set(t, cur)
      }

      for (const p of recovered) {
        const t = String(p.dt)
        const cur = byTime.get(t) ?? {
          time: t,
          observed: null,
          recovered: null,
          forecastMean: null,
          ciLower: null,
          ciUpper: null,
          stockout: false,
          isForecast: false,
        }
        cur.recovered = Number(p.value) || 0
        byTime.set(t, cur)
      }

      for (const p of forecast) {
        const t = String(p.dt)
        forecastTimes.add(t)
        const cur = byTime.get(t) ?? {
          time: t,
          observed: null,
          recovered: null,
          forecastMean: null,
          ciLower: null,
          ciUpper: null,
          stockout: false,
          isForecast: true,
        }
        cur.forecastMean = Number(p.value) || 0
        byTime.set(t, cur)
      }

      // quyết định isForecast: chỉ là forecast nếu KHÔNG có observed/recovered
      const all = Array.from(byTime.values()).map((p) => {
        const hasHist = p.observed !== null || p.recovered !== null
        const isFc = !hasHist && forecastTimes.has(p.time)
        return { ...p, isForecast: isFc }
      })

      const sorted = mergeSorted(all)
      setHistoryData(sorted.filter((p) => !p.isForecast))
      setForecastData(sorted.filter((p) => p.isForecast))

      // Accuracy panel (nếu có SKU)
      if (pid) {
        const acc = await loadAccuracyFromApi({ timeRange, storeId, sku })
        setAccuracyInfo(acc)
      } else {
        setAccuracyInfo(null)
      }

      // IMPORTANT: cập nhật Inventory Suggestion bằng backend
      await refreshInventoryFromApi()
    } finally {
      setLoading(false)
    }
  }, [aggregation, refreshInventoryFromApi, sku, storeId, timeRange])

  // Khi đổi Lead time / Service level và đã chọn SKU => gọi lại backend để update panel
  useEffect(() => {
    const pid = toNullableInt(sku)
    if (!pid) return
    refreshInventoryFromApi()
  }, [inventoryInputs, sku, storeId, timeRange, refreshInventoryFromApi])

  // Nếu chưa chọn SKU => cho phép mock “đỡ trống”
  useEffect(() => {
    const pid = toNullableInt(sku)
    if (pid) return
    const denom = Math.max(1, chartData.length)
    const meanPerPoint = Math.max(1, Math.round((kpis.observedSum ?? 0) / denom))
    setInventoryOutputs(computeInventoryOutputs(inventoryInputs, meanPerPoint))
  }, [inventoryInputs, chartData.length, kpis.observedSum, sku])

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
    kpis,
    inventoryInputs,
    setInventoryInputs,
    inventoryOutputs,
    replenishmentOpen,
    setReplenishmentOpen,
    loadData,
    loading,
    accuracyInfo,
    metaData,
  }
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const value = useInternalState()
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboardState(): DashboardState {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboardState must be used within DashboardProvider')
  return ctx
}