import React from 'react'
import { Box, Grid, Card, CardContent, Typography, TextField, MenuItem, Button } from '@mui/material'
import { useDashboardState } from '../../../hooks/useDashboardState'
import KpiCard from './KpiCard'
import ReplenishmentModal from './ReplenishmentModal'

export default function KPIInventoryPanel() {
  const { kpis, inventoryInputs, setInventoryInputs, inventoryOutputs, replenishmentOpen, setReplenishmentOpen } =
    useDashboardState()

  const format2Decimals = (value: unknown) => {
    const n = typeof value === 'number' ? value : Number(value)
    if (!Number.isFinite(n)) return '—'
    return n.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return (
    <Box>
      <Grid container spacing={1} sx={{ mb: 2 }}>
        <Grid item xs={6}>
          <KpiCard label="Observed sum (period)" value={format2Decimals(kpis.observedSum)} />
        </Grid>

        <Grid item xs={6}>
          <KpiCard label="Stockout hours" value={kpis.stockoutHours ?? '—'} />
        </Grid>

        <Grid item xs={6}>
          <KpiCard label="Recovered demand" value={format2Decimals(kpis.recoveredSum)} />
        </Grid>

        <Grid item xs={6}>
          <KpiCard label="Forecast next horizon" value={format2Decimals(kpis.forecastNextHorizon)} />
        </Grid>
      </Grid>

      <Card sx={{ borderRadius: 2, boxShadow: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
            Inventory Suggestion
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Lead time (hours)"
                size="small"
                type="number"
                fullWidth
                value={inventoryInputs.leadTimeHours}
                onChange={(e) => setInventoryInputs({ ...inventoryInputs, leadTimeHours: Number(e.target.value) })}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                select
                size="small"
                label="Service level"
                fullWidth
                value={inventoryInputs.serviceLevel}
                onChange={(e) => setInventoryInputs({ ...inventoryInputs, serviceLevel: Number(e.target.value) as any })}
              >
                <MenuItem value={0.9}>0.90</MenuItem>
                <MenuItem value={0.95}>0.95</MenuItem>
                <MenuItem value={0.99}>0.99</MenuItem>
              </TextField>
            </Grid>
          </Grid>

          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption">Lead-time demand</Typography>
              <Typography sx={{ fontWeight: 600 }}>{inventoryOutputs.leadTimeDemandMean}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption">Safety stock</Typography>
              <Typography sx={{ fontWeight: 600 }}>{inventoryOutputs.safetyStock}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption">Reorder Point (ROP)</Typography>
              <Typography sx={{ fontWeight: 600 }}>{inventoryOutputs.rop}</Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption">Suggested order qty</Typography>
              <Typography sx={{ fontWeight: 600 }}>{inventoryOutputs.suggestedOrder}</Typography>
            </Grid>
          </Grid>

          <Grid container sx={{ mt: 2 }}>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => setReplenishmentOpen(true)}
                  sx={{ minWidth: 180, height: 40, fontSize: '0.875rem', textTransform: 'none' }}
                >
                  Generate Plan
                </Button>

                <Button
                  variant="outlined"
                  onClick={() => console.log('export csv')}
                  sx={{ minWidth: 160, height: 40, fontSize: '0.875rem', textTransform: 'none' }}
                >
                  Export CSV
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <ReplenishmentModal open={replenishmentOpen} onClose={() => setReplenishmentOpen(false)} />
    </Box>
  )
}
