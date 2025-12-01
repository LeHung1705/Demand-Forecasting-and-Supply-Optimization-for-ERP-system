import { generateMockData, computeKpisFromData, ChartPoint } from '../utils/mockDashboardData'

export async function loadMockDashboard() : Promise<{ data: ChartPoint[]; kpis: any }> {
  // simulate delay
  await new Promise(r => setTimeout(r, 300))
  const data = generateMockData(24 * 14)
  const kpis = computeKpisFromData(data)
  return { data, kpis }
}
