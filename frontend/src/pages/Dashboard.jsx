import React, { useEffect, useMemo } from 'react';
import './Dashboard.css';
import { useDashboardState } from '../hooks/useDashboardState';

// --- 1. IMPORT COMPONENT MỚI ---
// Đảm bảo đường dẫn đúng với cấu trúc thư mục của bạn
import AdvancedMetricsPanel from '../components/feature/dashboard/AdvancedMetricsPanel';

const Dashboard = () => {
  const {
    loading,
    kpis,
    chartData,
    loadData,
    timeRange,
    storeId,
    sku
    // Lưu ý: Không cần lấy accuracyInfo ở đây nữa vì AdvancedMetricsPanel tự lấy rồi
  } = useDashboardState();

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatNumber = (n) => {
    const num = Number(n) || 0;
    return num.toLocaleString('vi-VN');
  };

  const formatMoney = (n) => {
    const num = Number(n) || 0;
    return num.toLocaleString('vi-VN');
  };

  const latestTrend = useMemo(() => {
    if (!chartData || chartData.length === 0) return [];
    return [...chartData].reverse().slice(0, 10);
  }, [chartData]);

  return (
    <div className="dashboard">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="page-title">Dashboard Tổng Quan</h2>
        <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
           Range: {timeRange.toUpperCase()} | Store: {storeId === 'all' ? 'All' : storeId} | SKU: {sku || 'All'}
        </span>
      </div>

      {loading && (
        <p className="text-secondary">Đang tải dữ liệu từ Backend...</p>
      )}

      {/* --- PHẦN KPI CARDS --- */}
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#4caf50' }}>📦</div>
          <div className="stat-content">
            <h3>Tổng sản phẩm</h3>
            <p className="stat-value">{formatNumber(kpis.product_count || 0)}</p>
            <p className="stat-change neutral">Active Products</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#2196f3' }}>🏬</div>
          <div className="stat-content">
            <h3>Tổng cửa hàng</h3>
            <p className="stat-value">{formatNumber(kpis.store_count || 0)}</p>
            <p className="stat-change neutral">Active Stores</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ff9800' }}>💰</div>
          <div className="stat-content">
            <h3>Doanh thu (Observed)</h3>
            <p className="stat-value">{formatMoney(kpis.observedSum || 0)}</p>
            <p className="stat-change neutral">
               Trong {timeRange} qua
            </p>
          </div>
        </div>

        {/* --- 2. THAY THẾ TOÀN BỘ LOGIC CARD ACCURACY CŨ BẰNG COMPONENT MỚI --- */}
        <div className="stat-card" style={{ padding: 0, overflow: 'hidden' }}>
           {/* Component này tự động kết nối Hook để hiển thị Accuracy */}
           <AdvancedMetricsPanel />
        </div>

      </div>

      <div className="dashboard-content">
        <div className="card">
          <h3>Xu hướng doanh thu (10 ngày gần nhất)</h3>
          {!loading && latestTrend.length === 0 && (
            <p className="text-secondary">Chưa có dữ liệu hiển thị.</p>
          )}
          {!loading && latestTrend.length > 0 && (
            <div style={{ maxHeight: 260, overflow: 'auto', marginTop: 12 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Date</th>
                    <th style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #eee' }}>Sales</th>
                    <th style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #eee' }}>Forecast</th>
                  </tr>
                </thead>
                <tbody>
                  {latestTrend.map((row, index) => (
                    <tr key={index}>
                      <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{row.time}</td>
                      <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #f3f3f3', fontWeight: 'bold' }}>
                        {formatMoney(row.observed)}
                      </td>
                      <td style={{ padding: 8, textAlign: 'right', borderBottom: '1px solid #f3f3f3', color: '#888' }}>
                         {row.forecastMean ? formatMoney(row.forecastMean) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <h3>Thông tin tồn kho (Inventory)</h3>
          <p className="text-secondary">
             Logic này đang được tính toán trong Hook (inventoryOutputs).
          </p>
        </div>
        
        {/* XÓA PHẦN CARD ADVANCED METRICS CŨ Ở DƯỚI NÀY (NẾU CÓ) */}
      </div>
    </div>
  );
};

export default Dashboard;