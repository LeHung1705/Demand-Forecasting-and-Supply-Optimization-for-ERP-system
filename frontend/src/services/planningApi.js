// src/services/planningApi.js
const BASE_URL = 'http://localhost:8000/api/v1/planning';

export async function getReplenishmentPlan(timeRange = '30d', storeId = null) {
  // Xây dựng URL query string
  let url = `${BASE_URL}/replenishment?time_range=${timeRange}`;
  
  if (storeId) {
    url += `&store_id=${storeId}`;
  }

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error('Failed to fetch planning data');
  }
  return res.json();
}