import { subHours, formatISO } from 'date-fns'

export type ChartPoint = {
  time: string // ISO or YYYY-MM-DD
  observed: number | null
  recovered?: number | null
  forecastMean?: number | null
  ciLower?: number | null
  ciUpper?: number | null
  stockout?: boolean
  isForecast?: boolean
}

export function generateMockData(hours = 24 * 7, start = new Date()): ChartPoint[] {
  const data: ChartPoint[] = []

  for (let i = hours - 1; i >= 0; i--) {
    const t = subHours(start, i)
    const base = 20 + 10 * Math.sin((i / 24) * Math.PI * 2)
    let observed = Math.max(0, Math.round(base + (Math.random() - 0.5) * 8))
    if (Math.random() < 0.06) observed = 0

    const recovered =
      observed === 0
        ? Math.round(base * (0.6 + Math.random() * 0.6))
        : Math.round(observed + (Math.random() - 0.3) * 5)

    data.push({
      time: formatISO(t),
      observed,
      recovered,
      stockout: observed === 0,
      forecastMean: null,
      ciLower: null,
      ciUpper: null,
      isForecast: false,
    })
  }

  // append some future forecast points (next 7 days hourly)
  for (let j = 1; j <= 24 * 7; j++) {
    const t = subHours(start, -j)
    const trend = 20 + 8 * Math.sin(((hours + j) / 24) * Math.PI * 2)
    const mean = Math.round(trend + (Math.random() - 0.5) * 6)
    const sd = Math.round(mean * 0.25)
    data.push({
      time: formatISO(t),
      observed: null,
      recovered: null,
      forecastMean: mean,
      ciLower: Math.max(0, mean - sd),
      ciUpper: mean + sd,
      stockout: false,
      isForecast: true,
    })
  }

  return data
}

export function computeKpisFromData(data: ChartPoint[]) {
  const observedSum = (data || []).reduce((s, d) => s + (d.observed ?? 0), 0)
  const stockoutHours = (data || []).filter((d) => d.stockout).length
  const recoveredSum = (data || []).reduce((s, d) => s + (d.recovered ?? 0), 0)

  const last = (data || []).slice(-24 * 7)
  const forecastNextHorizon = last.reduce((s, d) => s + (d.forecastMean ?? 0), 0)

  return { observedSum, stockoutHours, recoveredSum, forecastNextHorizon }
}
