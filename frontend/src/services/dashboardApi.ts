import { ChartPoint, computeKpisFromData } from '../utils/mockDashboardData'
import analyticsService, { type TrendsResponse } from './analyticsService'

type LoadParams = {
  timeRange?: '7d' | '30d' | '90d'
  aggregation?: 'hourly' | 'daily'
  storeId?: string
  sku?: string
}

function toIntOrUndefined(v?: string): number | undefined {
  const s = String(v ?? '').trim()
  if (!s) return undefined
  const n = Number(s)
  if (!Number.isFinite(n)) return undefined
  // ✅ allow 0
  return Math.trunc(n)
}

export async function loadDashboardFromApi(
  params: LoadParams = {}
): Promise<{ data: ChartPoint[]; kpis: any }> {
  const store_id =
    params.storeId && params.storeId !== 'all'
      ? toIntOrUndefined(params.storeId)
      : undefined

  const product_id = params.sku ? toIntOrUndefined(params.sku) : undefined

  const res: TrendsResponse = await analyticsService.getTrends({
    metric: 'sales_by_day',
    time_range: params.timeRange ?? '7d',
    store_id,
    product_id,
  })

  const points = Array.isArray(res?.points) ? res.points : []

  const data: ChartPoint[] = points.map((p) => ({
    time: p.key,
    observed: Number(p.value) || 0,

    recovered: null,
    forecastMean: null,
    ciLower: null,
    ciUpper: null,
    stockout: false,
  }))

  const kpis = computeKpisFromData(data)
  return { data, kpis }
}
// --- BỔ SUNG THÊM HÀM NÀY VÀO CUỐI FILE ---

export async function loadAccuracyFromApi(params: LoadParams = {}): Promise<any> {
  const store_id = params.storeId && params.storeId !== 'all' ? params.storeId : '';
  const product_id = params.sku ? params.sku : '';
  const time_range = params.timeRange ?? '30d';

  // Tạo URL Query String
  const query = new URLSearchParams({
    time_range,
    ...(store_id ? { store_id: String(store_id) } : {}),
    ...(product_id ? { product_id: String(product_id) } : {}),
  }).toString();

  try {
    // Gọi thẳng vào Backend URL (Port 8000)
    const res = await fetch(`http://localhost:8000/api/v1/analytics/accuracy?${query}`);
    if (!res.ok) {
      throw new Error('Failed to fetch accuracy');
    }
    return await res.json();
  } catch (error) {
    console.error("Accuracy API Error:", error);
    return { available: false, message: "Lỗi kết nối API" };
  }
}