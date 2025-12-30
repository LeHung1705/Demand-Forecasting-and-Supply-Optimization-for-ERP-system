// File: frontend/src/components/dashboard/InventorySuggestion.tsx

import React, { useState } from 'react';
import { 
  Box, Button, Card, CardContent, Grid, 
  MenuItem, TextField, Typography, CircularProgress 
} from '@mui/material';
import axios from 'axios';

// --- ĐỊNH NGHĨA KIỂU DỮ LIỆU ---
interface InventoryMetrics {
  lead_time_demand: number;
  safety_stock: number;
  reorder_point: number;
  suggested_order_qty?: number;
}

interface Props {
  selectedStoreId: number | string | null | undefined;
  selectedProductId: number | string | null | undefined;
}

// Hàm format số cho đẹp
const fmt = (n: number | undefined) => 
  n !== undefined ? n.toLocaleString('vi-VN', { maximumFractionDigits: 2 }) : '-';

export default function InventorySuggestion({ selectedStoreId, selectedProductId }: Props) {
  // State Input
  const [leadTime, setLeadTime] = useState<number>(24);
  const [serviceLevel, setServiceLevel] = useState<number>(0.95);
  
  // State Kết quả & Loading
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<InventoryMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  // HÀM GỌI API QUAN TRỌNG NHẤT
  const handleGeneratePlan = async () => {
    // 1. Reset lỗi và loading
    setError(null);
    setLoading(true);

    // 2. Kiểm tra Store/Product (Convert sang số)
    const sId = Number(selectedStoreId) || 0;
    const pId = Number(selectedProductId) || 0;

    console.log("BUTTON CLICKED! Parameters:", { sId, pId, leadTime, serviceLevel });

    if (pId === 0) {
      setError("Vui lòng chọn SKU (Product ID) trên thanh menu trước!");
      setLoading(false);
      return;
    }

    try {
      // 3. GỌI API THẬT
      // Lưu ý: Sửa lại URL localhost:8000 nếu port backend của bạn khác
      const response = await axios.post('http://localhost:8000/api/v1/inventory/plan', {
        store_id: sId,
        product_id: pId,
        lead_time_hours: leadTime,
        service_level: serviceLevel,
        time_range: '30d'
      });

      console.log("API Response:", response.data);
      
      // 4. Cập nhật kết quả vào State
      setMetrics(response.data.metrics);

    } catch (err: any) {
      console.error("API Error:", err);
      setError("Lỗi gọi API: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card sx={{ borderRadius: 2, boxShadow: 2, height: '100%' }}>
      <CardContent>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
          Inventory Suggestion (Real API)
        </Typography>

        {/* INPUTS */}
        <Grid container spacing={2} mb={2}>
          <Grid item xs={6}>
            <TextField
              label="Lead time (hours)"
              type="number"
              size="small"
              fullWidth
              value={leadTime}
              onChange={(e) => setLeadTime(Number(e.target.value))}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              select
              label="Service Level"
              size="small"
              fullWidth
              value={serviceLevel}
              onChange={(e) => setServiceLevel(Number(e.target.value))}
            >
              <MenuItem value={0.90}>90%</MenuItem>
              <MenuItem value={0.95}>95%</MenuItem>
              <MenuItem value={0.99}>99%</MenuItem>
            </TextField>
          </Grid>
        </Grid>

        {/* ERROR MESSAGE */}
        {error && (
          <Typography color="error" variant="body2" mb={2}>
            ⚠️ {error}
          </Typography>
        )}

        {/* RESULTS GRID */}
        <Grid container spacing={2} mb={2}>
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" display="block">Lead-time demand</Typography>
            <Typography fontWeight="bold">{metrics ? fmt(metrics.lead_time_demand) : '-'}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" display="block">Safety stock</Typography>
            <Typography fontWeight="bold">{metrics ? fmt(metrics.safety_stock) : '-'}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" display="block">ROP</Typography>
            <Typography fontWeight="bold" color="primary">{metrics ? fmt(metrics.reorder_point) : '-'}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" display="block">Suggested Qty</Typography>
            <Typography fontWeight="bold" color="success.main">
               {metrics ? fmt(metrics.reorder_point) : '-'}
            </Typography>
          </Grid>
        </Grid>

        {/* BUTTON */}
        <Button 
          variant="contained" 
          fullWidth 
          onClick={handleGeneratePlan}
          disabled={loading}
          startIcon={loading && <CircularProgress size={20} color="inherit"/>}
        >
          {loading ? 'Calculating...' : 'Generate Plan'}
        </Button>

      </CardContent>
    </Card>
  );
}