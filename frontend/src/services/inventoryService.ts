import api from './api'

export type TimeRange = '7d' | '30d' | '90d'

export interface InventoryPlanInput {
  store_id: number | null
  product_id: number | null
  lead_time_hours: number
  service_level: number
  time_range?: TimeRange
}

export interface InventoryPlanMetrics {
  lead_time_hours: number
  lead_time_days: number
  service_level: number
  z_score: number
  days_count: number
  avg_daily_sales: number
  stddev_daily_sales: number
  lead_time_demand: number
  safety_stock: number
  reorder_point: number
  suggested_order_qty?: number
}

export interface InventoryPlanResponse {
  meta: {
    time_range: string
    from_date?: string | null
    to_date?: string | null
    store_id?: number | null
    product_id?: number | null
    [k: string]: any
  }
  metrics: InventoryPlanMetrics
}

export async function fetchInventoryPlan(payload: InventoryPlanInput): Promise<InventoryPlanResponse> {
  // api.post đã unwrap response.data (xem frontend/src/services/api.js)
  return await api.post('/api/v1/inventory/plan', payload)
}