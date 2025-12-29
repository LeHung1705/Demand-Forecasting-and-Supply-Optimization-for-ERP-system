import React, { useEffect, useMemo, useState } from 'react'
import './Dashboard.css'
import { useDashboardState } from '../hooks/useDashboardState'
import { APP_CONFIG } from '../utils/constants'
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import AdvancedMetricsPanel from '../components/feature/dashboard/AdvancedMetricsPanel';

const Dashboard = () => {
  const {
    loading,
    kpis,
    chartData,
    loadData,
    timeRange,
    setTimeRange,
    storeId,
    setStoreId,
    sku,
    setSku,
    showForecast,
    setShowForecast,
    metaData,
  } = useDashboardState()

  // search dropdown state
  const [storeQuery, setStoreQuery] = useState('')
  const [productQuery, setProductQuery] = useState('')
  const [storeOptions, setStoreOptions] = useState([])
  const [productOptions, setProductOptions] = useState([])

  // export modal state
  const [exportOpen, setExportOpen] = useState(false)
  const [exportStoreId, setExportStoreId] = useState('all')
  const [exportProductId, setExportProductId] = useState('')
  const [exportDays, setExportDays] = useState(7)
  const [exportPipeline, setExportPipeline] = useState('forecast_only')
  const [exporting, setExporting] = useState(false)

  const apiBase = APP_CONFIG.API_URL || 'http://localhost:8000'

  useEffect(() => {
    // initialize export defaults from current filters
    setExportStoreId(storeId || 'all')
    setExportProductId(sku || '')
  }, [storeId, sku])

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ query: storeQuery, limit: '50' })
        const res = await fetch(`${apiBase}/api/v1/meta/stores?${qs.toString()}`)
        const json = await res.json()
        setStoreOptions(Array.isArray(json?.items) ? json.items : [])
      } catch {
        setStoreOptions([])
      }
    }, 250)
    return () => clearTimeout(t)
  }, [storeQuery, apiBase])

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const qs = new URLSearchParams({ query: productQuery, limit: '50' })
        const res = await fetch(`${apiBase}/api/v1/meta/products?${qs.toString()}`)
        const json = await res.json()
        setProductOptions(Array.isArray(json?.items) ? json.items : [])
      } catch {
        setProductOptions([])
      }
    }, 250)
    return () => clearTimeout(t)
  }, [productQuery, apiBase])

  const formatNumber = (n) => {
    const num = Number(n) || 0
    return num.toLocaleString('vi-VN')
  }

  const formatMoney = (n) => {
    const num = Number(n) || 0
    return num.toLocaleString('vi-VN', { style: 'currency', currency: 'VND' })
  }

  const visibleSeries = useMemo(() => {
    const arr = Array.isArray(chartData) ? chartData : []
    return showForecast ? arr : arr.filter((p) => !p.isForecast)
  }, [chartData, showForecast])

  const latestTrend = useMemo(() => {
    if (!visibleSeries || visibleSeries.length === 0) return []
    const hist = visibleSeries.filter((p) => !p.isForecast)
    return [...hist].reverse().slice(0, 10)
  }, [visibleSeries])

  const handleExport = async () => {
    setExporting(true)
    try {
      const body = {
        time_range: timeRange,
        store_id:
          exportStoreId && exportStoreId !== 'all' && exportStoreId !== '' ? Number(exportStoreId) : null,
        product_id: exportProductId && exportProductId !== '' ? Number(exportProductId) : null,
        forecast_days: Number(exportDays) || 7,
        pipeline: exportPipeline,
      }

      const res = await fetch(`${apiBase}/api/v1/export/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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

      setExportOpen(false)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h2 className="page-title">Dashboard Tổng Quan</h2>
        <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
          Range: {timeRange.toUpperCase()} | Store: {storeId === 'all' ? 'All' : storeId} | SKU: {sku || 'All'}
        </span>
      </div>

      {/* CONTROL BAR */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Time range</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd' }}
            >
              <option value="7d">7d</option>
              <option value="30d">30d</option>
              <option value="90d">90d</option>
            </select>
          </div>

          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Store (search)</label>
            <input
              value={storeQuery}
              onChange={(e) => setStoreQuery(e.target.value)}
              placeholder="type to search store..."
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: 220 }}
            />
            <div style={{ marginTop: 8 }}>
              <select
                value={storeId}
                onChange={(e) => setStoreId(e.target.value)}
                style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: 220 }}
              >
                <option value="all">All stores</option>
                {storeOptions.map((id) => (
                  <option key={id} value={String(id)}>
                    Store {id}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Product (search)</label>
            <input
              value={productQuery}
              onChange={(e) => setProductQuery(e.target.value)}
              placeholder="type to search SKU..."
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: 220 }}
            />
            <div style={{ marginTop: 8 }}>
              <select
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: 220 }}
              >
                <option value="">All products</option>
                {productOptions.map((id) => (
                  <option key={id} value={String(id)}>
                    SKU {id}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', userSelect: 'none' }}>
              <input type="checkbox" checked={showForecast} onChange={(e) => setShowForecast(e.target.checked)} />
              Show Forecast (future)
            </label>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={loadData}
              style={{
                padding: '9px 20px',
                background: '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              LOAD DATA
            </button>

            <button
              onClick={() => setExportOpen(true)}
              style={{
                padding: '9px 20px',
                background: '#2e7d32',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              EXPORT REPORT
            </button>
          </div>
        </div>

        {metaData?.from_date && metaData?.to_date && (
          <div style={{ marginTop: 12, fontSize: '0.9em', color: '#666', background: '#f5f5f5', padding: '8px 12px', borderRadius: 6 }}>
            📅 {metaData.from_date} → {metaData.to_date} • max_dt: <b>{metaData.max_dt}</b>
          </div>
        )}
      </div>

      {loading && <p className="text-secondary">Đang tải dữ liệu từ Backend...</p>}

      {/* KPI CARDS */}
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ff9800' }}>💰</div>
          <div className="stat-content">
            <h3>Doanh thu (Observed)</h3>
            <p className="stat-value">{formatMoney(kpis.observedSum || 0)}</p>
            <p className="stat-change neutral">Trong {timeRange}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#4caf50' }}>🧩</div>
          <div className="stat-content">
            <h3>Recovered Sum</h3>
            <p className="stat-value">{formatMoney(kpis.recoveredSum || 0)}</p>
            <p className="stat-change neutral">Trong {timeRange}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#673ab7' }}>🔮</div>
          <div className="stat-content">
            <h3>Forecast (Next horizon)</h3>
            <p className="stat-value">{formatMoney(kpis.forecastNextHorizon || 0)}</p>
            <p className="stat-change neutral">Dummy</p>
          </div>
        </div>

        <div className="stat-card" style={{ padding: 0, overflow: 'hidden' }}>
           {/* Component này tự động kết nối Hook để hiển thị Accuracy */}
           <AdvancedMetricsPanel />
        </div>

      </div>

      {/* CHART */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Observed / Recovered / Forecast</h3>
        <div style={{ width: '100%', height: 360 }}>
          <ResponsiveContainer>
            <LineChart data={visibleSeries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="observed" name="Observed" stroke="#1976d2" dot={false} />
              <Line type="monotone" dataKey="recovered" name="Recovered" stroke="#2e7d32" dot={false} />
              {showForecast && (
                <Line type="monotone" dataKey="forecastMean" name="Forecast (future)" stroke="#ff9800" dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* LATEST TABLE */}
      <div className="dashboard-content">
        <div className="card">
          <h3>Xu hướng doanh thu (10 ngày gần nhất)</h3>
          {!loading && latestTrend.length === 0 && <p className="text-secondary">Chưa có dữ liệu hiển thị.</p>}
          {!loading && latestTrend.length > 0 && (
            <div style={{ maxHeight: 260, overflow: 'auto', marginTop: 12 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Date</th>
                    <th style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #eee' }}>Observed</th>
                    <th style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #eee' }}>Recovered</th>
                  </tr>
                </thead>
                <tbody>
                  {latestTrend.map((row, index) => (
                    <tr key={index}>
                      <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{row.time}</td>
                      <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #f3f3f3', fontWeight: 'bold' }}>
                        {formatMoney(row.observed || 0)}
                      </td>
                      <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #f3f3f3' }}>
                        {row.recovered != null ? formatMoney(row.recovered) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* EXPORT MODAL */}
      {exportOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            zIndex: 9999,
          }}
          onClick={() => (!exporting ? setExportOpen(false) : null)}
        >
          <div
            className="card"
            style={{ width: 520, maxWidth: '100%', padding: 16 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginTop: 0 }}>Export Report</h3>

            <div style={{ display: 'grid', gap: 12 }}>
              <div>
                <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Store</label>
                <select
                  value={exportStoreId}
                  onChange={(e) => setExportStoreId(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: '100%' }}
                >
                  <option value="all">All stores</option>
                  {storeOptions.map((id) => (
                    <option key={id} value={String(id)}>
                      Store {id}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Product</label>
                <select
                  value={exportProductId}
                  onChange={(e) => setExportProductId(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: '100%' }}
                >
                  <option value="">All products</option>
                  {productOptions.map((id) => (
                    <option key={id} value={String(id)}>
                      SKU {id}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Forecast days</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={exportDays}
                  onChange={(e) => setExportDays(Number(e.target.value))}
                  style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: '100%' }}
                />
              </div>

              <div>
                <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 6 }}>Pipeline</label>
                <select
                  value={exportPipeline}
                  onChange={(e) => setExportPipeline(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd', width: '100%' }}
                >
                  <option value="forecast_only">Forecast</option>
                  <option value="train_df_then_forecast">Training DF + Forecast</option>
                  <option value="train_ldr_then_train_df_then_forecast">Training LDR + Training DF + Forecast</option>
                  <option value="adaptive_recommend">Adaptive (recommend)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
                <button
                  onClick={() => setExportOpen(false)}
                  disabled={exporting}
                  style={{
                    padding: '9px 16px',
                    background: '#bdbdbd',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: exporting ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold',
                  }}
                >
                  Cancel
                </button>

                <button
                  onClick={handleExport}
                  disabled={exporting}
                  style={{
                    padding: '9px 16px',
                    background: '#2e7d32',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: exporting ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold',
                  }}
                >
                  {exporting ? 'Downloading...' : 'Download CSV'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard