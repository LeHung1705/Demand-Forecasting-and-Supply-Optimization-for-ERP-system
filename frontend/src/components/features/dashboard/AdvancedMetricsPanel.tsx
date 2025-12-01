import React from 'react'
import { List, ListItem, ListItemText, Typography, Stack } from '@mui/material'
import AnalyticsIcon from '@mui/icons-material/Analytics'
import AppCard from '../../layout/AppCard'

export default function AdvancedMetricsPanel() {
  return (
    <AppCard sx={{ height: '100%' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <AnalyticsIcon color="action" />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Advanced Metrics</Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Model diagnostics and performance metrics (hidden for demo)
      </Typography>

      <List dense>
        <ListItem>
          <ListItemText primary="MAPE" secondary="4.2%" />
        </ListItem>
        <ListItem>
          <ListItemText primary="RMSE" secondary="12.4" />
        </ListItem>
        <ListItem>
          <ListItemText primary="Bias" secondary="-0.5" />
        </ListItem>
      </List>
    </AppCard>
  )
}
