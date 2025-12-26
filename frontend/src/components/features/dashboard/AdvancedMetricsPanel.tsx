// File: src/components/feature/dashboard/AdvancedMetricsPanel.tsx

import React from 'react'
import { 
  List, ListItem, ListItemText, Typography, Stack, 
  CircularProgress, Box, Divider 
} from '@mui/material'
import AnalyticsIcon from '@mui/icons-material/Analytics'
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';

// QUAN TRỌNG: Import Hook để lấy dữ liệu
import { useDashboardState } from '../../../hooks/useDashboardState'
// Lưu ý: Nếu AppCard của bạn không dùng MUI thì đổi thành div className="card"
// Ở đây tôi giữ AppCard theo code cũ của bạn, nhưng bọc style để giống Dashboard
import AppCard from '../../layout/AppCard'

export default function AdvancedMetricsPanel() {
  // 1. Lấy dữ liệu từ Hook (không cần truyền props)
  const { accuracyInfo, sku, loading } = useDashboardState()

  // 2. Tính toán trạng thái hiển thị
  // Đang tải nếu: có chọn SKU, đang loading, và chưa có info
  const isCalculating = loading && sku && !accuracyInfo; 
  const hasData = accuracyInfo?.available === true && accuracyInfo?.metrics;

  return (
    // Style height 100% để thẻ này cao bằng các thẻ khác
    <AppCard sx={{ height: '100%', boxShadow: 'none', border: '1px solid #eee' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <AnalyticsIcon color="primary" />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Advanced Metrics
        </Typography>
      </Stack>

      {/* TRƯỜNG HỢP 1: ĐANG TẢI */}
      {isCalculating ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
          <CircularProgress size={30} sx={{ mb: 2 }} />
          <Typography variant="body2" color="text.secondary">
            Đang tính toán độ chính xác...
          </Typography>
        </Box>
      ) : hasData ? (
        /* TRƯỜNG HỢP 2: CÓ DỮ LIỆU THẬT */
        <>
          <Typography variant="body2" sx={{ mb: 2, color: '#2e7d32', display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircleIcon fontSize="small" />
            {accuracyInfo.message}
          </Typography>
          
          <List dense disablePadding>
            <ListItem divider>
              <ListItemText 
                primary="Accuracy Score" 
                secondary={
                  <Typography variant="body1" sx={{ fontWeight: 'bold', color: '#28a745' }}>
                    {accuracyInfo.metrics.accuracy_score}%
                  </Typography>
                }
              />
            </ListItem>

            <ListItem divider>
              <ListItemText 
                primary="MAPE (Sai số)" 
                secondary={
                  <Typography variant="body1" sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
                    {accuracyInfo.metrics.mape}%
                  </Typography>
                }
              />
            </ListItem>

            <ListItem divider>
              <ListItemText 
                primary="RMSE" 
                secondary={accuracyInfo.metrics.rmse.toFixed(2)} 
              />
            </ListItem>

            <ListItem>
              <ListItemText 
                primary="Dữ liệu mẫu (n)" 
                secondary={`${accuracyInfo.metrics.n} ngày`} 
              />
            </ListItem>
          </List>
        </>
      ) : (
        /* TRƯỜNG HỢP 3: CHƯA CÓ DỮ LIỆU / CHƯA CHỌN SKU */
        <Box sx={{ py: 3, textAlign: 'center', opacity: 0.7 }}>
           <WarningIcon color="action" sx={{ fontSize: 40, mb: 1, opacity: 0.5 }} />
           <Typography variant="body2" color="text.secondary">
             {sku 
               ? (accuracyInfo?.message || "Không đủ dữ liệu để tính toán") 
               : "Vui lòng chọn 1 Sản phẩm (SKU) cụ thể để xem độ chính xác thuật toán."}
           </Typography>
        </Box>
      )}
    </AppCard>
  )
}