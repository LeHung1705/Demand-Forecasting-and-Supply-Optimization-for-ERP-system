import React from 'react'

import AppLayout from '../components/layout/AppLayout'
import Header from '../components/layout/Header'
import ControlPanel from '../components/features/dashboard/ControlPanel'
import DemandChart from '../components/charts/DemandChart'
import KPIInventoryPanel from '../components/features/dashboard/KPIInventoryPanel'
import { Grid, Box } from '@mui/material'
import { DashboardProvider, useDashboardState } from '../hooks/useDashboardState'
import CovariatesPanel from '../components/features/dashboard/CovariatesPanel'
import AdvancedMetricsPanel from '../components/features/dashboard/AdvancedMetricsPanel'

function DashboardInner() {
  const { loadData, runRecoveryAndForecast, setReplenishmentOpen } = useDashboardState()
  return (
    <AppLayout>
      <Header onLoad={loadData} onRun={runRecoveryAndForecast} onExport={() => console.log('Export report')} />

      <ControlPanel />

      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <DemandChart />
        </Grid>
        <Grid item xs={12} md={4}>
          <KPIInventoryPanel />
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <CovariatesPanel />
          </Grid>
          <Grid item xs={12} md={6}>
            <AdvancedMetricsPanel />
          </Grid>
        </Grid>
      </Box>
    </AppLayout>
  )
}

export default function DashboardPage() {
  return (
    <DashboardProvider>
      <DashboardInner />
    </DashboardProvider>
  )
}
