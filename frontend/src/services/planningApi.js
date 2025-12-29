// src/services/planningApi.js

// Tốt nhất nên lấy từ biến môi trường (Environment Variable) để dễ deploy sau này
// const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const BASE_URL = 'http://localhost:8000/api/v1/planning';

/**
 * Lấy kế hoạch nhập hàng
 * @param {string} timeRange - Khoảng thời gian (7d, 30d, 90d)
 * @param {number|string|null} storeId - ID cửa hàng (Optional)
 * @param {number|string|null} productId - ID sản phẩm (Optional) - MỚI BỔ SUNG
 */
export async function getReplenishmentPlan(timeRange = '30d', storeId = null, productId = null) {
  // 1. Sử dụng URLSearchParams để tạo query string chuẩn xác
  const params = new URLSearchParams();
  
  params.append('time_range', timeRange);

  // Kiểm tra chặt chẽ: !== null và !== '' để nhận cả số 0 (Store ID 0)
  if (storeId !== null && storeId !== undefined && storeId !== '') {
    params.append('store_id', storeId);
  }

  // Thêm Product ID (Logic mới)
  if (productId !== null && productId !== undefined && productId !== '') {
    params.append('product_id', productId);
  }

  // 2. Tạo URL hoàn chỉnh
  const url = `${BASE_URL}/replenishment?${params.toString()}`;

  // 3. Gọi Fetch
  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Thêm Authorization header tại đây nếu sau này cần login
      },
    });

    if (!res.ok) {
      // Đọc lỗi từ Backend trả về (nếu có) thay vì ném lỗi chung chung
      const errorData = await res.json().catch(() => ({})); 
      throw new Error(errorData.detail || `Error fetching data: ${res.status}`);
    }

    return await res.json();
  } catch (error) {
    console.error("API Error:", error);
    throw error; // Ném lỗi ra để Frontend (DemandPlanning.jsx) hiển thị alert
  }
}