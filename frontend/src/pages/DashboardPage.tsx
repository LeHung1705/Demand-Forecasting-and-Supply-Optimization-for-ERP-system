import React, { useState } from 'react'

import AppLayout from '../components/layout/AppLayout'
import Header from '../components/layout/Header'
import ControlPanel from '../components/features/dashboard/ControlPanel'
import DemandChart from '../components/charts/DemandChart'
import KPIInventoryPanel from '../components/features/dashboard/KPIInventoryPanel'
import { Grid, Typography, Box } from '@mui/material'
import { DashboardProvider, useDashboardState } from '../hooks/useDashboardState'
import ExportReportModal from '../components/features/dashboard/ExportReportModal'

function DashboardInner() {
  const { loadData, metaData } = useDashboardState()
  const [exportOpen, setExportOpen] = useState(false)

  const lastHistory = metaData?.last_history
  const lastHistoryText = lastHistory?.year
    ? `${String(lastHistory.year).padStart(4, '0')}-${String(lastHistory.month).padStart(2, '0')}-${String(
        lastHistory.day
      ).padStart(2, '0')}`
    : null

  return (
    <AppLayout>
      <Header onLoad={loadData} onExport={() => setExportOpen(true)} />

      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Last history date (for AI params):{' '}
          <b>{lastHistoryText ?? '(click Load Data to compute last_dt)'}</b>
          {lastHistoryText ? (
            <>
              {' '}| year={lastHistory.year}, month={lastHistory.month}, day={lastHistory.day}
            </>
          ) : null}
        </Typography>
      </Box>

      <ControlPanel />

      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <DemandChart />
        </Grid>
        <Grid item xs={12} md={4}>
          <KPIInventoryPanel />
        </Grid>
      </Grid>

      <ExportReportModal open={exportOpen} onClose={() => setExportOpen(false)} />
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
