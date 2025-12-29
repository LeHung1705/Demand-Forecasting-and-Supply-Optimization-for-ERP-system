import React from 'react'
import { Box, Button, ButtonGroup, IconButton, TextField, Typography } from '@mui/material'
import StorefrontIcon from '@mui/icons-material/Storefront'
import DownloadIcon from '@mui/icons-material/Download'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { useDashboardState } from '../../hooks/useDashboardState'

type Props = {
  onLoad?: () => void
  onExport?: () => void
}

export default function Header({ onLoad, onExport }: Props) {
  const { timeRange, setTimeRange, storeId, setStoreId, sku, setSku } = useDashboardState()

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton size="large" sx={{ bgcolor: 'primary.main', color: 'white' }}>
            <StorefrontIcon />
          </IconButton>
          <Box>
            <Typography variant="h6">FreshRetailNet-50K Forecast Demo</Typography>
            <Typography variant="body2" color="text.secondary">
              Dashboard (CSV + DuckDB)
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Button variant="outlined" startIcon={<CloudUploadIcon />} onClick={onLoad}>
            Load Data
          </Button>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={onExport}>
            Export Report
          </Button>
        </Box>
      </Box>

      <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <ButtonGroup size="small" variant="outlined" aria-label="time-range">
          <Button onClick={() => setTimeRange('7d')} color={timeRange === '7d' ? 'primary' : 'inherit'}>
            7D
          </Button>
          <Button onClick={() => setTimeRange('30d')} color={timeRange === '30d' ? 'primary' : 'inherit'}>
            30D
          </Button>
          <Button onClick={() => setTimeRange('90d')} color={timeRange === '90d' ? 'primary' : 'inherit'}>
            90D
          </Button>
        </ButtonGroup>

        <TextField size="small" label="Store (all or id)" value={storeId} onChange={(e) => setStoreId(e.target.value)} />
        <TextField size="small" label="SKU (blank or id)" value={sku} onChange={(e) => setSku(e.target.value)} />
      </Box>
    </Box>
  )
}
