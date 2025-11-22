import React from 'react'
import { Stack, Chip, Typography, Box } from '@mui/material'
import CloudQueueIcon from '@mui/icons-material/CloudQueue'
import AppCard from '../../layout/AppCard'

export default function CovariatesPanel() {
  return (
    <AppCard sx={{ height: '100%' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <CloudQueueIcon color="action" />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Covariates</Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Placeholder for covariates influencing demand (promotions, weather, holidays)
      </Typography>

      <Box>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip label="Discounts" color="primary" sx={{ mb: 1 }} />
          <Chip label="Weather" sx={{ mb: 1 }} />
          <Chip label="Holiday" color="secondary" sx={{ mb: 1 }} />
        </Stack>
      </Box>
    </AppCard>
  )
}
