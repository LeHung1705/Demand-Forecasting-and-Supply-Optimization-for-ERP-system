import React from 'react'
import { Card, CardContent, Typography, Box } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, CartesianGrid, Legend } from 'recharts'
import { useTheme } from '@mui/material/styles'
import { useDashboardState } from '../../hooks/useDashboardState'

export default function DemandChart() {
  const theme = useTheme()
  const { chartData, showRecovered, showForecastCI, showStockout } = useDashboardState()

  if (!chartData || chartData.length === 0) {
    return (
      <Card>
        <CardContent sx={{ minHeight: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">No data loaded</Typography>
            <Typography variant="body2" color="text.secondary">Click 'Load Data' to view the demand series.</Typography>
          </Box>
        </CardContent>
      </Card>
    )
  }

  // map to recharts-friendly objects
  const points = chartData.map(d => ({
    time: new Date(d.time).toLocaleString(),
    observed: d.observed ?? null,
    recovered: d.recovered ?? null,
    forecast: d.forecastMean ?? null,
    ciLower: d.ciLower ?? null,
    ciUpper: d.ciUpper ?? null,
    stockout: d.stockout ?? false,
  }))

  const tooltipFormatter = (value: any, name: string) => {
    return [value, name]
  }

  return (
    <Card sx={{ borderRadius: 2, boxShadow: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>Demand & Forecast</Typography>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={points} margin={{ top: 8, right: 20, left: 0, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6b7280' }} tickFormatter={(t) => {
              try { const d = new Date(t); return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' }) } catch { return t }
            }} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip formatter={tooltipFormatter} labelStyle={{ fontSize: 12 }} contentStyle={{ borderRadius: 8 }} />
            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: 12 }} />
            {showForecastCI && (
              <Area dataKey="ciUpper" type="monotone" stroke="none" fill={theme.palette.primary.light} fillOpacity={0.10} />
            )}
            <Line name="Observed" type="monotone" dataKey="observed" stroke={theme.palette.primary.main} dot={{ r: 2 }} strokeWidth={2} />
            {showRecovered && (
              <Line name="Recovered" type="monotone" dataKey="recovered" stroke={theme.palette.secondary.main} strokeDasharray="4 4" dot={false} />
            )}
            {showForecastCI && (
              <Line name="Forecast" type="monotone" dataKey="forecast" stroke={theme.palette.primary.dark} strokeWidth={2} dot={false} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
