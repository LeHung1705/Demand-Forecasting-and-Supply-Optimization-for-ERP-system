import React, { useEffect, useState } from 'react'
import { getReplenishmentPlan } from '../services/planningApi'
import { optimizationService } from '../services/optimizationService'
import * as XLSX from 'xlsx'
import './Dashboard.css'

const DemandPlanning = () => {
  // --- STATE ---
  const [planData, setPlanData] = useState([])
  const [metaData, setMetaData] = useState(null)
  const [loading, setLoading] = useState(false)

  // 1. FILTER CHUNG (Dùng cho cả Basic & Advanced)
  const [timeRange, setTimeRange] = useState('30d')
  const [storeId, setStoreId] = useState('')      // Input Store
  const [productId, setProductId] = useState('')  // <--- MỚI: Input Product

  // 2. STATE CHẾ ĐỘ NÂNG CAO (ADVANCED)
  const [isAdvancedMode, setIsAdvancedMode] = useState(false)
  const [constraints, setConstraints] = useState({
    budget: 50000000,
    max_inventory: 50000000,
    lead_time: 7,
  })
  const [optimizedData, setOptimizedData] = useState(null)

  // Hàm format tiền tệ
  const formatCurrency = (val) =>
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(val || 0))

  const downloadExcel = (rows, fileName, sheetName = 'Data') => {
    const worksheet = XLSX.utils.json_to_sheet(rows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
    const arrayBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
    const blob = new Blob([arrayBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  }

  const handleExportExcel = () => {
    const today = new Date().toISOString().slice(0, 10)

    if (!isAdvancedMode) {
      if (!planData || planData.length === 0) {
        alert('Không có dữ liệu để export. Vui lòng bấm Phân tích trước.')
        return
      }

      const rows = planData.map((row) => ({
        Store_ID: row.store_id,
        Product_ID: row.product_id,
        Avg_Daily_Sales: Number(row.avg_daily_sales || 0),
        Stock_Availability_Hours: Number(row.stock_availability_hours || 0),
        Risk_Level: row.risk_level,
        Suggested_Replenishment_Value: Number(row.suggested_replenishment || 0),
      }))

      downloadExcel(rows, `bao-cao-nhu-cau-basic-${today}.xlsx`, 'Basic')
      return
    }

    if (!optimizedData || !(optimizedData.data || []).length) {
      alert('Không có dữ liệu tối ưu để export. Vui lòng bấm Chạy Tối ưu trước.')
      return
    }

    const rows = (optimizedData.data || []).map((row) => ({
      Store_ID: row.store_id,
      Product_ID: row.product_id,
      Risk_Level: row.risk_level,
      Optimal_Order_Value: Number(row.optimal_order_value || 0),
      Selected_Value: Number(row.selected_value || 0),
      Note: row.note,
    }))

    downloadExcel(rows, `toi-uu-cung-ung-advanced-${today}.xlsx`, 'Advanced')
  }

  // Xử lý input số an toàn
  const getStoreId = () => (storeId && storeId.trim() !== '' ? Number(storeId) : null)
  const getProductId = () => (productId && productId.trim() !== '' ? Number(productId) : null)

  // --- HÀM 1: LOAD DỮ LIỆU CƠ BẢN (BASIC) ---
  const loadBasicData = async () => {
    setLoading(true)
    try {
      // Gọi API cũ, truyền thêm productId nếu có
      // Lưu ý: Bạn cần kiểm tra xem hàm getReplenishmentPlan trong planningApi.js đã hỗ trợ tham số thứ 3 chưa
      // Nếu chưa, API backend vẫn nhận query params ?product_id=... nên thường sẽ tự động chạy nếu truyền đúng object
      const sid = getStoreId()
      const pid = getProductId()
      
      // Giả sử hàm getReplenishmentPlan nhận (timeRange, storeId, productId)
      // Nếu file api của bạn chưa update, hãy sửa lại file planningApi.js một chút hoặc truyền object
      const res = await getReplenishmentPlan(timeRange, sid, pid) 
      
      setPlanData(res.data || [])
      setMetaData(res.meta || null)
    } catch (err) {
      console.error(err)
      alert('Lỗi tải dữ liệu: ' + (err?.message || 'Kiểm tra lại kết nối'))
    } finally {
      setLoading(false)
    }
  }

  // --- HÀM 2: CHẠY TỐI ƯU HÓA (ADVANCED) ---
  const handleOptimize = async () => {
    setLoading(true)
    try {
      const pid = getProductId()
      const payload = {
        time_range: timeRange,
        store_id: getStoreId(),
        product_ids: pid ? [pid] : null, // Backend nhận mảng [int], nên nếu có ID thì bỏ vào mảng
        constraints: {
          budget: Number(constraints.budget),
          max_inventory: Number(constraints.max_inventory),
          lead_time: Number(constraints.lead_time),
        },
      }
      const res = await optimizationService.runSupplyOptimization(payload)
      setOptimizedData(res)
    } catch (err) {
      console.error(err)
      alert('Lỗi tối ưu hóa: ' + (err?.message || 'Kiểm tra lại API'))
    } finally {
      setLoading(false)
    }
  }

  // Tự động load lại khi switch chế độ (chỉ load Basic)
  useEffect(() => {
    if (!isAdvancedMode) {
      // Nếu muốn tự động load khi mở trang thì bỏ comment dòng dưới
      // loadBasicData() 
    }
  }, [isAdvancedMode])

  return (
    <div className="dashboard">
      {/* HEADER */}
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title">
            {isAdvancedMode ? '⚡ Tối ưu hóa Cung ứng (Advanced)' : '📊 Báo cáo Nhu cầu & Rủi ro (Basic)'}
          </h2>
          <p style={{ color: '#666', fontSize: '14px' }}>
            {isAdvancedMode
              ? 'Thuật toán tự động cân đối ngân sách để chọn ra danh sách nhập hàng hiệu quả nhất.'
              : 'Xem dữ liệu lịch sử và cảnh báo các mã hàng sắp hết trong kho (Stock < 5h).'}
          </p>
        </div>

        <button
          onClick={() => setIsAdvancedMode(!isAdvancedMode)}
          style={{
            padding: '10px 20px',
            background: isAdvancedMode ? '#673ab7' : '#607d8b',
            color: 'white',
            border: 'none',
            borderRadius: 30,
            cursor: 'pointer',
            fontWeight: 'bold',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}
        >
          {isAdvancedMode ? '🔄 Về chế độ Cơ bản' : '🚀 Chuyển sang Tối ưu hóa'}
        </button>
      </div>

      {/* FILTER CONTROL PANEL */}
      <div className="card" style={{ marginBottom: 20, padding: 20 }}>
        <div style={{ display: 'flex', gap: 15, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          
          {/* 1. Time Range */}
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 5 }}>Phạm vi:</label>
            <select 
              value={timeRange} 
              onChange={(e) => setTimeRange(e.target.value)} 
              style={{ padding: '8px 12px', borderRadius: 4, border: '1px solid #ccc' }}
            >
              <option value="7d">7 ngày qua</option>
              <option value="30d">30 ngày qua</option>
              <option value="90d">90 ngày qua</option>
            </select>
          </div>

          {/* 2. Store ID Input */}
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 5 }}>Store ID:</label>
            <input
              type="number"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              placeholder="All"
              style={{ padding: '8px 12px', width: 80, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </div>

          {/* 3. Product ID Input (MỚI BỔ SUNG) */}
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 5 }}>Product ID:</label>
            <input
              type="number"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              placeholder="All"
              style={{ padding: '8px 12px', width: 80, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </div>

          {/* NÚT CHẠY LỆNH */}
          {!isAdvancedMode ? (
            <>
              <button
                onClick={loadBasicData}
                style={{ 
                  padding: '9px 25px', background: '#2196f3', color: 'white', 
                  border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 'bold' 
                }}
              >
                🔍 Phân tích
              </button>

              <button
                onClick={handleExportExcel}
                disabled={!planData || planData.length === 0}
                style={{
                  padding: '9px 18px',
                  background: (!planData || planData.length === 0) ? '#bdbdbd' : '#2e7d32',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: (!planData || planData.length === 0) ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                }}
              >
                ⬇️ Export Excel
              </button>
            </>
          ) : (
            // Các input thêm cho chế độ Advanced
            <>
              <div style={{borderLeft: '2px solid #ddd', paddingLeft: 15, display: 'flex', gap: 15}}>
                <div>
                  <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 5, color: '#673ab7' }}>Ngân sách (VNĐ):</label>
                  <input
                    type="number"
                    value={constraints.budget}
                    onChange={(e) => setConstraints({ ...constraints, budget: e.target.value })}
                    style={{ padding: '8px 12px', width: 120, borderRadius: 4, border: '1px solid #673ab7' }}
                  />
                </div>
                <div>
                  <label style={{ fontWeight: 'bold', display: 'block', marginBottom: 5, color: '#673ab7' }}>Kho max (Val):</label>
                  <input
                    type="number"
                    value={constraints.max_inventory}
                    onChange={(e) => setConstraints({ ...constraints, max_inventory: e.target.value })}
                    style={{ padding: '8px 12px', width: 120, borderRadius: 4, border: '1px solid #673ab7' }}
                  />
                </div>
              </div>
              
              <button
                onClick={handleOptimize}
                style={{ 
                  padding: '9px 25px', background: '#673ab7', color: 'white', 
                  border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 'bold',
                  boxShadow: '0 2px 4px rgba(103, 58, 183, 0.3)'
                }}
              >
                ⚡ Chạy Tối ưu
              </button>

              <button
                onClick={handleExportExcel}
                disabled={!optimizedData || !(optimizedData.data || []).length}
                style={{
                  padding: '9px 18px',
                  background: (!optimizedData || !(optimizedData.data || []).length) ? '#bdbdbd' : '#2e7d32',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: (!optimizedData || !(optimizedData.data || []).length) ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                }}
              >
                ⬇️ Export Excel
              </button>
            </>
          )}
        </div>

        {/* META DATA INFO */}
        {!isAdvancedMode && metaData && (
          <div style={{ marginTop: 15, fontSize: '0.9em', color: '#666', background: '#f5f5f5', padding: '8px 15px', borderRadius: 4 }}>
            📅 Dữ liệu từ: <strong>{metaData.from_date}</strong> đến <strong>{metaData.to_date}</strong> • Số ngày có bán hàng: {metaData.bounds?.available_days}
          </div>
        )}
      </div>

      {/* --- BẢNG KẾT QUẢ --- */}
      <div className="card">
        {loading && <p style={{ padding: 30, textAlign: 'center', color: '#666' }}>⏳ Đang tính toán dữ liệu...</p>}

        {/* BẢNG BASIC */}
        {!loading && !isAdvancedMode && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #e9ecef' }}>
                  <th style={{ padding: 12, textAlign: 'left' }}>Store</th>
                  <th style={{ padding: 12, textAlign: 'left' }}>Product</th>
                  <th style={{ padding: 12, textAlign: 'right' }}>Sức bán TB (Ngày)</th>
                  <th style={{ padding: 12, textAlign: 'center' }}>Giờ có hàng (6-22h)</th>
                  <th style={{ padding: 12, textAlign: 'center' }}>Rủi ro</th>
                  <th style={{ padding: 12, textAlign: 'right' }}>Gợi ý nhập (VNĐ)</th>
                </tr>
              </thead>
              <tbody>
                {planData.length === 0 ? (
                  <tr><td colSpan={6} style={{ padding: 30, textAlign: 'center', color: '#888' }}>Chưa có dữ liệu. Vui lòng bấm Phân tích.</td></tr>
                ) : (
                  planData.map((row, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee', backgroundColor: row.risk_level === 'high' ? '#fff5f5' : 'white' }}>
                      <td style={{ padding: 12 }}>{row.store_id}</td>
                      <td style={{ padding: 12, fontWeight: 'bold' }}>{row.product_id}</td>
                      <td style={{ padding: 12, textAlign: 'right' }}>{formatCurrency(row.avg_daily_sales)}</td>
                      <td style={{ padding: 12, textAlign: 'center' }}>
                        <span style={{ padding: '4px 8px', borderRadius: 4, background: '#eee' }}>{row.stock_availability_hours}h</span>
                      </td>
                      <td style={{ padding: 12, textAlign: 'center' }}>
                        <span style={{ 
                          color: row.risk_level === 'high' ? '#d32f2f' : (row.risk_level === 'medium' ? '#f57c00' : '#388e3c'),
                          fontWeight: 'bold'
                        }}>
                          {row.risk_level === 'high' ? 'Nguy cấp' : (row.risk_level === 'medium' ? 'Cảnh báo' : 'Ổn định')}
                        </span>
                      </td>
                      <td style={{ padding: 12, textAlign: 'right', fontWeight: 'bold', color: '#1976d2' }}>
                        {formatCurrency(row.suggested_replenishment)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* BẢNG ADVANCED */}
        {!loading && isAdvancedMode && optimizedData && (
          <div>
            <div style={{ padding: 15, background: '#ede7f6', borderBottom: '1px solid #d1c4e9', color: '#512da8', display: 'flex', justifyContent: 'space-between' }}>
              <span>🎯 <strong>KẾT QUẢ TỐI ƯU:</strong> Đã chọn {optimizedData.items_count} mã hàng</span>
              <span>Tổng tiền: <b>{formatCurrency(optimizedData.total_selected_value)}</b> (Ngân sách: {formatCurrency(constraints.budget)})</span>
            </div>
            
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f3e5f5', borderBottom: '2px solid #e1bee7' }}>
                  <th style={{ padding: 12, textAlign: 'left' }}>Store</th>
                  <th style={{ padding: 12, textAlign: 'left' }}>Product</th>
                  <th style={{ padding: 12, textAlign: 'center' }}>Độ ưu tiên (Risk)</th>
                  <th style={{ padding: 12, textAlign: 'right' }}>Cần nhập (Optimal)</th>
                  <th style={{ padding: 12, textAlign: 'right' }}>Được duyệt (Selected)</th>
                  <th style={{ padding: 12, textAlign: 'left' }}>Ghi chú</th>
                </tr>
              </thead>
              <tbody>
                {(optimizedData.data || []).map((row, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 12 }}>{row.store_id}</td>
                    <td style={{ padding: 12, fontWeight: 'bold' }}>{row.product_id}</td>
                    <td style={{ padding: 12, textAlign: 'center' }}>{row.risk_level}</td>
                    <td style={{ padding: 12, textAlign: 'right', color: '#888' }}>{formatCurrency(row.optimal_order_value)}</td>
                    <td style={{ padding: 12, textAlign: 'right', fontWeight: 'bold', color: '#673ab7', fontSize: '1.1em' }}>
                      {formatCurrency(row.selected_value)}
                    </td>
                    <td style={{ padding: 12, color: '#e65100', fontStyle: 'italic' }}>{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default DemandPlanning