import React from 'react'
import { Box, Button, ButtonGroup, IconButton, MenuItem, Select, SelectChangeEvent, TextField, Typography } from '@mui/material'
import StorefrontIcon from '@mui/icons-material/Storefront'
import DownloadIcon from '@mui/icons-material/Download'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { useDashboardState } from '../../hooks/useDashboardState'

type Props = {
  onLoad?: () => void
  onRun?: () => void
  onExport?: () => void
}

export default function Header({ onLoad, onRun, onExport }: Props) {
  const { timeRange, setTimeRange, storeId, setStoreId, sku, setSku } = useDashboardState()

  const handleStoreChange = (e: SelectChangeEvent) => setStoreId(e.target.value as string)

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton size="large" sx={{ bgcolor: 'primary.main', color: 'white' }}>
            <StorefrontIcon />
          </IconButton>
          <Box>
            <Typography variant="h6">FreshRetailNet-50K Forecast Demo</Typography>
            <Typography variant="body2" color="text.secondary">Demand forecasting & inventory planning demo for ERP course</Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button variant="outlined" startIcon={<CloudUploadIcon />} onClick={onLoad}>Load Data</Button>
          <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={onRun}>Run Recovery + Forecast</Button>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={onExport}>Export Report</Button>
        </Box>
      </Box>

      <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <ButtonGroup size="small" variant="outlined" aria-label="time-range">
          <Button onClick={() => setTimeRange('7d')} color={timeRange === '7d' ? 'primary' : 'inherit'}>7D</Button>
          <Button onClick={() => setTimeRange('30d')} color={timeRange === '30d' ? 'primary' : 'inherit'}>30D</Button>
          <Button onClick={() => setTimeRange('90d')} color={timeRange === '90d' ? 'primary' : 'inherit'}>90D</Button>
        </ButtonGroup>

        <Select value={storeId} size="small" onChange={handleStoreChange} variant="outlined">
          <MenuItem value="all">All stores</MenuItem>
          <MenuItem value="store-1">Store 1</MenuItem>
          <MenuItem value="store-2">Store 2</MenuItem>
        </Select>

        <TextField size="small" placeholder="Search SKU" value={sku} onChange={e => setSku(e.target.value)} />
      </Box>
    </Box>
  )
}
