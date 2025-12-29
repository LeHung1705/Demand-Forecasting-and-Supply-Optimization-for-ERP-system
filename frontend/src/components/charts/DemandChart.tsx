import React, { useMemo } from 'react'
import { Card, CardContent, Typography, Box } from '@mui/material'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  CartesianGrid,
  Legend,
  ReferenceArea,
} from 'recharts'
import { useTheme } from '@mui/material/styles'
import { useDashboardState } from '../../hooks/useDashboardState'

function toEpochMs(s: any): number | null {
  const t = Date.parse(String(s))
  return Number.isFinite(t) ? t : null
}

function format2(n: unknown): string {
  const v = typeof n === 'number' ? n : Number(n)
  if (!Number.isFinite(v)) return '—'
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function DemandChart() {
  const theme = useTheme()
  const { chartData, showRecovered, showForecastCI, showStockout } = useDashboardState()

  const points = useMemo(() => {
    const arr = Array.isArray(chartData) ? chartData : []
    return arr
      .map((d) => {
        const ts = toEpochMs(d.time)
        if (ts === null) return null
        return {
          ts,
          observed: d.observed ?? null,
          recovered: d.recovered ?? null,
          forecast: d.forecastMean ?? null,
          ciLower: d.ciLower ?? null,
          ciUpper: d.ciUpper ?? null,
          stockout: d.stockout ?? false,
          isForecast: d.isForecast ?? false,
        }
      })
      .filter(Boolean) as any[]
  }, [chartData])

  const forecastShade = useMemo(() => {
    if (!showForecastCI || !points.length) return null
    const firstForecast = points.find((p) => p.isForecast)
    if (!firstForecast) return null
    const x1 = firstForecast.ts
    const x2 = points[points.length - 1].ts

    const yVals: number[] = []
    for (const p of points) {
      const candidates = [p.observed, p.recovered, p.forecast, p.ciUpper, p.ciLower]
      for (const v of candidates) {
        if (typeof v === 'number' && Number.isFinite(v)) yVals.push(v)
      }
    }
    const yMax = Math.max(1, ...(yVals.length ? yVals : [1]))
    return { x1, x2, y1: 0, y2: yMax }
  }, [points, showForecastCI])

  if (!points || points.length === 0) {
    return (
      <Card>
        <CardContent sx={{ minHeight: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              No data loaded
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Click 'Load Data' to view the demand series.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card sx={{ borderRadius: 2, boxShadow: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
          Demand & Forecast
        </Typography>

        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={points} margin={{ top: 8, right: 20, left: 0, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />

            <XAxis
              dataKey="ts"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickFormatter={(ts) => {
                try {
                  const d = new Date(ts)
                  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' })
                } catch {
                  return String(ts)
                }
              }}
            />

            <YAxis
              tick={{ fontSize: 11, fill: '#6b7280' }}
              tickFormatter={(v) => format2(v)}
            />

            <Tooltip
              formatter={(value: any, name: string) => {
                // ✅ làm tròn 2 chữ số cho mọi chỉ số hiển thị trong tooltip
                if (typeof value === 'number') return [format2(value), name]
                return [value, name]
              }}
              labelFormatter={(ts) => {
                try {
                  return new Date(Number(ts)).toLocaleString()
                } catch {
                  return String(ts)
                }
              }}
              labelStyle={{ fontSize: 12 }}
              contentStyle={{ borderRadius: 8 }}
            />

            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: 12 }} />

            {/* ✅ Shade "future" region so users immediately see it's forecast */}
            {forecastShade && (
              <ReferenceArea
                x1={forecastShade.x1}
                x2={forecastShade.x2}
                y1={forecastShade.y1}
                y2={forecastShade.y2}
                fill="#fff3e0"
                fillOpacity={0.45}
                strokeOpacity={0}
                label={{
                  value: 'FUTURE (Forecast)',
                  position: 'insideTopRight',
                  fill: theme.palette.text.secondary,
                  fontSize: 12,
                }}
              />
            )}

            {showForecastCI && (
              <>
                <Area dataKey="ciUpper" type="monotone" stroke="none" fill={theme.palette.warning.light} fillOpacity={0.10} />
                <Area dataKey="ciLower" type="monotone" stroke="none" fill={theme.palette.warning.light} fillOpacity={0.10} />
              </>
            )}

            <Line name="Observed" type="monotone" dataKey="observed" stroke={theme.palette.primary.main} dot={{ r: 2 }} strokeWidth={2} />

            {showRecovered && (
              <Line name="Recovered" type="monotone" dataKey="recovered" stroke={theme.palette.secondary.main} strokeDasharray="4 4" dot={false} />
            )}

            {showForecastCI && (
              <Line name="Forecast (future)" type="monotone" dataKey="forecast" stroke={theme.palette.warning.main} strokeWidth={3} strokeDasharray="8 6" dot={false} />
            )}

            {showStockout && (
              <Line name="Stockout" type="stepAfter" dataKey="stockout" stroke="transparent" dot={false} hide />
            )}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
