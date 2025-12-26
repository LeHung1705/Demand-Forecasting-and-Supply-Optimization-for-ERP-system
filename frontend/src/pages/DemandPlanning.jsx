import React, { useEffect, useState } from 'react';
import './Dashboard.css';
import { getReplenishmentPlan } from '../services/planningService';

const DemandPlanning = () => {
  const [planData, setPlanData] = useState([]);
  const [metaData, setMetaData] = useState(null);
  const [loading, setLoading] = useState(false);

  const [timeRange, setTimeRange] = useState('30d');
  const [storeId, setStoreId] = useState('');     // cho phép nhập 0
  const [productId, setProductId] = useState(''); // ví dụ 4

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await getReplenishmentPlan({
        time_range: timeRange,
        store_id: storeId,
        product_id: productId,
        page,
        page_size: pageSize,
      });

      setPlanData(res?.data || []);
      setMetaData(res?.meta || null);
    } catch (e) {
      alert('Lỗi tải dữ liệu phân tích: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  // auto load khi đổi timeRange
  useEffect(() => {
    setPage(1);
    // eslint-disable-next-line
  }, [timeRange]);

  // auto load khi đổi page/pageSize
  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [page, pageSize]);

  const formatCurrency = (v) =>
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(v || 0));

  const riskBadge = (level) => {
    if (level === 'high') return <span style={{ color: 'red', fontWeight: 700 }}>⚠️ Nguy cấp</span>;
    if (level === 'medium') return <span style={{ color: 'orange', fontWeight: 700 }}>⚠️ Cảnh báo</span>;
    return <span style={{ color: 'green' }}>✅ Ổn định</span>;
  };

  const totalCount = Number(metaData?.total_count ?? 0);
  const totalPages = totalCount > 0 ? Math.max(1, Math.ceil(totalCount / Number(pageSize || 1))) : null;

  const handleExportCSV = () => {
    const headers = [
      'Store ID',
      'Product ID',
      'Avg Daily Sales',
      'Stock Hours',
      'Risk Level',
      'Suggested Budget',
    ];

    const escapeCSV = (value) => {
      const str = String(value ?? '');
      return `"${str.replace(/"/g, '""')}"`;
    };

    const rows = (planData || []).map((row) => {
      const cells = [
        row?.store_id ?? '',
        row?.product_id ?? '',
        row?.avg_daily_sales ?? '',
        row?.stock_availability_hours ?? '',
        row?.risk_level ?? '',
        row?.suggested_replenishment ?? '',
      ];
      return cells.map(escapeCSV).join(',');
    });

    const csvString = '\uFEFF' + [headers.map(escapeCSV).join(','), ...rows].join('\r\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'replenishment_plan.csv';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="dashboard">
      <div style={{ marginBottom: 16 }}>
        <h2 className="page-title">Báo cáo phân tích nhu cầu</h2>
        <p className="text-secondary">
          Gợi ý nhập hiện tính theo <b>giá trị (sale_amount)</b>. Nếu muốn “số lượng”, cần actual_qty hoặc price.
        </p>
      </div>

      {/* FILTER */}
      <div className="card" style={{ marginBottom: 20, padding: 20 }}>
        <div style={{ display: 'flex', gap: 18, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontWeight: 700, display: 'block', marginBottom: 6 }}>Phạm vi</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              style={{ padding: 8, minWidth: 180 }}
            >
              <option value="7d">7 ngày gần nhất</option>
              <option value="30d">30 ngày gần nhất</option>
              <option value="90d">90 ngày gần nhất</option>
            </select>
          </div>

          <div>
            <label style={{ fontWeight: 700, display: 'block', marginBottom: 6 }}>Store ID</label>
            <input
              type="number"
              placeholder="VD: 0"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              style={{ padding: 8, width: 120 }}
            />
          </div>

          <div>
            <label style={{ fontWeight: 700, display: 'block', marginBottom: 6 }}>Product ID</label>
            <input
              type="number"
              placeholder="VD: 4"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              style={{ padding: 8, width: 120 }}
            />
          </div>

          <button
            onClick={loadData}
            style={{
              padding: '9px 18px',
              background: '#2196f3',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 800,
            }}
          >
            🔍 Phân tích ngay
          </button>

          <button
            onClick={handleExportCSV}
            style={{
              padding: '9px 18px',
              background: '#4caf50',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 800,
            }}
          >
            ⬇️ Export CSV
          </button>
        </div>

        {/* PAGINATION */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 14, flexWrap: 'wrap' }}>
          <span className="text-secondary" style={{ fontSize: '0.9rem' }}>
            Trang: <b>{page}</b>
            {totalPages ? (
              <> / <b>{totalPages}</b> (total: <b>{totalCount}</b>)</>
            ) : null}
          </span>

          <button
            onClick={() => setPage((p) => Math.max(1, Number(p || 1) - 1))}
            disabled={loading || page <= 1}
            style={{
              padding: '7px 12px',
              background: '#eee',
              border: '1px solid #ddd',
              borderRadius: 6,
              cursor: loading || page <= 1 ? 'not-allowed' : 'pointer',
              fontWeight: 700,
            }}
          >
            ◀ Prev
          </button>

          <button
            onClick={() => setPage((p) => {
              const next = Number(p || 1) + 1;
              if (totalPages) return Math.min(totalPages, next);
              return next;
            })}
            disabled={loading || (totalPages ? page >= totalPages : false)}
            style={{
              padding: '7px 12px',
              background: '#eee',
              border: '1px solid #ddd',
              borderRadius: 6,
              cursor: loading || (totalPages ? page >= totalPages : false) ? 'not-allowed' : 'pointer',
              fontWeight: 700,
            }}
          >
            Next ▶
          </button>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="text-secondary" style={{ fontSize: '0.9rem' }}>Rows:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPage(1);
                setPageSize(Number(e.target.value));
              }}
              style={{ padding: 6, minWidth: 100 }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </div>
        </div>

        {/* META */}
        {metaData && (
          <div
            style={{
              marginTop: 14,
              fontSize: '0.9em',
              color: '#555',
              background: '#f9f9f9',
              padding: 10,
              borderRadius: 6,
            }}
          >
            <b>ℹ️ Range backend:</b> {metaData.from_date} → {metaData.to_date}
            {metaData?.bounds?.available_days !== undefined && (
              <> • available_days: <b>{metaData.bounds.available_days}</b></>
            )}
            {metaData?.total_count !== undefined && (
              <> • total: <b>{metaData.total_count}</b></>
            )}
          </div>
        )}
      </div>

      {/* TABLE */}
      <div className="card">
        {loading ? (
          <p style={{ padding: 16 }}>Đang tính toán...</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: 12, textAlign: 'left' }}>Store</th>
                <th style={{ padding: 12, textAlign: 'left' }}>Product</th>
                <th style={{ padding: 12, textAlign: 'right' }}>Avg/day (Value)</th>
                <th style={{ padding: 12, textAlign: 'center' }}>Giờ có hàng (6–22)</th>
                <th style={{ padding: 12, textAlign: 'left' }}>Rủi ro</th>
                <th style={{ padding: 12, textAlign: 'right' }}>Ngân sách đề xuất (Est. Budget)</th>
              </tr>
            </thead>
            <tbody>
              {planData.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: 18, textAlign: 'center' }}>
                    Không có dữ liệu.
                  </td>
                </tr>
              ) : (
                planData.map((row, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 12 }}>{row.store_id ?? '-'}</td>
                    <td style={{ padding: 12, fontWeight: 800 }}>{row.product_id}</td>

                    <td style={{ padding: 12, textAlign: 'right' }}>
                      {formatCurrency(row.avg_daily_sales)}
                    </td>

                    <td style={{ padding: 12, textAlign: 'center' }}>
                      <span
                        style={{
                          padding: '4px 10px',
                          borderRadius: 999,
                          fontWeight: 800,
                          background: row.stock_availability_hours < 5 ? '#ffebee' : '#e8f5e9',
                          color: row.stock_availability_hours < 5 ? '#c62828' : '#2e7d32',
                        }}
                      >
                        {row.stock_availability_hours}h
                      </span>
                    </td>

                    <td style={{ padding: 12 }}>{riskBadge(row.risk_level)}</td>

                    <td style={{ padding: 12, textAlign: 'right', fontWeight: 900, color: '#1976d2' }}>
                      {row.suggested_replenishment > 0 ? formatCurrency(row.suggested_replenishment) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default DemandPlanning;
