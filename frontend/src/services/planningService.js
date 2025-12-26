import api from './api';

/**
 * GET /api/v1/planning/replenishment
 * params: time_range=7d|30d|90d, store_id, product_id, page, page_size
 */
export async function getReplenishmentPlan({ time_range = '30d', store_id, product_id, page = 1, page_size = 100 } = {}) {
  const params = { time_range };

  // ✅ cho phép store_id = 0
  if (store_id !== undefined && store_id !== null && store_id !== '') {
    params.store_id = Number(store_id);
  }

  if (product_id !== undefined && product_id !== null && product_id !== '') {
    params.product_id = Number(product_id);
  }

  if (page !== undefined && page !== null && page !== '') {
    params.page = Number(page);
  }

  if (page_size !== undefined && page_size !== null && page_size !== '') {
    params.page_size = Number(page_size);
  }

  // interceptor của api.js đã unwrap response.data rồi
  return await api.get('/api/v1/planning/replenishment', { params });
}
