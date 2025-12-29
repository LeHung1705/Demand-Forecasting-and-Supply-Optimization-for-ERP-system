import React, { useEffect, useMemo, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Stack,
  CircularProgress,
  Typography,
} from '@mui/material'
import { APP_CONFIG } from '../../../utils/constants'
import { useDashboardState } from '../../../hooks/useDashboardState'

type Props = {
  open: boolean
  onClose: () => void
}

type Pipeline =
  | 'forecast_only'
  | 'train_df_then_forecast'
  | 'train_ldr_then_train_df_then_forecast'
  | 'adaptive_recommend'

export default function ExportReportModal({ open, onClose }: Props) {
  const { timeRange, storeId, sku } = useDashboardState()
  const apiBase = APP_CONFIG.API_URL || 'http://localhost:8000'

  const [exporting, setExporting] = useState(false)

  const [storeQuery, setStoreQuery] = useState('')
  const [productQuery, setProductQuery] = useState('')
  const [storeOptions, setStoreOptions] = useState<number[]>([])
  const [productOptions, setProductOptions] = useState<number[]>([])

  const [exportStoreId, setExportStoreId] = useState<string>('all')
  const [exportProductId, setExportProductId] = useState<string>('')
  const [exportDays, setExportDays] = useState<number>(7)
  const [exportPipeline, setExportPipeline] = useState<Pipeline>('forecast_only')

  // init defaults when open
  useEffect(() => {
    if (!open) return
    setExportStoreId(storeId || 'all')
    setExportProductId(sku || '')
    setExportDays(7)
    setExportPipeline('forecast_only')
  }, [open, storeId, sku])

  // fetch store options (debounced)
  useEffect(() => {
    if (!open) return
    const t = window.setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ query: storeQuery || '', limit: '50' })
        const res = await fetch(`${apiBase}/api/v1/meta/stores?${qs.toString()}`)
        const json = await res.json()
        setStoreOptions(Array.isArray(json?.items) ? json.items : [])
      } catch {
        setStoreOptions([])
      }
    }, 250)
    return () => window.clearTimeout(t)
  }, [open, storeQuery, apiBase])

  // fetch product options (debounced)
  useEffect(() => {
    if (!open) return
    const t = window.setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ query: productQuery || '', limit: '50' })
        const res = await fetch(`${apiBase}/api/v1/meta/products?${qs.toString()}`)
        const json = await res.json()
        setProductOptions(Array.isArray(json?.items) ? json.items : [])
      } catch {
        setProductOptions([])
      }
    }, 250)
    return () => window.clearTimeout(t)
  }, [open, productQuery, apiBase])

  const canClose = useMemo(() => !exporting, [exporting])

  const handleDownload = async () => {
    setExporting(true)
    try {
      // ✅ Đây là các biến user nhập để backend trích xuất:
      const payload = {
        time_range: timeRange,
        store_id:
          exportStoreId && exportStoreId !== 'all' && exportStoreId !== ''
            ? Number(exportStoreId)
            : null,
        product_id: exportProductId && exportProductId !== '' ? Number(exportProductId) : null,
        forecast_days: Number(exportDays) || 7,
        pipeline: exportPipeline,
      }

      const res = await fetch(`${apiBase}/api/v1/export/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const txt = await res.text().catch(() => '')
        throw new Error(`Export failed (${res.status}): ${txt}`)
      }

      const blob = await res.blob()
      const cd = res.headers.get('content-disposition') || ''
      const m = /filename="?([^"]+)"?/i.exec(cd)
      const filename = m?.[1] || 'report.csv'

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)

      onClose()
    } finally {
      setExporting(false)
    }
  }

  return (
    <Dialog open={open} onClose={canClose ? onClose : undefined} maxWidth="sm" fullWidth>
      <DialogTitle>Export Report</DialogTitle>

      <DialogContent dividers>
        <Stack spacing={2}>
          <Typography variant="body2" color="text.secondary">
            Export based on current dashboard time_range: <b>{timeRange}</b>
          </Typography>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Search store"
              value={storeQuery}
              onChange={(e) => setStoreQuery(e.target.value)}
              fullWidth
            />
            <TextField
              select
              label="Store"
              value={exportStoreId}
              onChange={(e) => setExportStoreId(e.target.value)}
              fullWidth
            >
              <MenuItem value="all">All stores</MenuItem>
              {storeOptions.map((id) => (
                <MenuItem key={id} value={String(id)}>
                  Store {id}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Search product"
              value={productQuery}
              onChange={(e) => setProductQuery(e.target.value)}
              fullWidth
            />
            <TextField
              select
              label="Product"
              value={exportProductId}
              onChange={(e) => setExportProductId(e.target.value)}
              fullWidth
            >
              <MenuItem value="">All products</MenuItem>
              {productOptions.map((id) => (
                <MenuItem key={id} value={String(id)}>
                  SKU {id}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          <TextField
            type="number"
            label="Forecast days"
            value={exportDays}
            onChange={(e) => setExportDays(Number(e.target.value))}
            inputProps={{ min: 1, max: 365 }}
            fullWidth
          />

          <TextField
            select
            label="Pipeline"
            value={exportPipeline}
            onChange={(e) => setExportPipeline(e.target.value as Pipeline)}
            fullWidth
          >
            <MenuItem value="forecast_only">Forecast</MenuItem>
            <MenuItem value="train_df_then_forecast">Training DF + Forecast</MenuItem>
            <MenuItem value="train_ldr_then_train_df_then_forecast">Training LDR + Training DF + Forecast</MenuItem>
            <MenuItem value="adaptive_recommend">Adaptive (recommend)</MenuItem>
          </TextField>
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={exporting} color="inherit">
          Cancel
        </Button>
        <Button onClick={handleDownload} disabled={exporting} variant="contained">
          {exporting ? (
            <>
              <CircularProgress size={18} sx={{ mr: 1 }} /> Downloading...
            </>
          ) : (
            'Download CSV'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}