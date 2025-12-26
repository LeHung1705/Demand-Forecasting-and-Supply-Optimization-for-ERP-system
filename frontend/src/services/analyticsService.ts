import api from './api'

export type TrendsPoint = {
  key: string        // 'YYYY-MM-DD'
  value: number      // tổng sale_amount
}

export type TrendsResponse = {
  metric: string
  from_date: string
  to_date: string
  points: TrendsPoint[]
}

export type GetTrendsParams = {
  metric?: string
  time_range?: '7d' | '30d' | '90d'
  store_id?: number
  product_id?: number
}

const analyticsService = {
  getDashboard: async (params: any = {}) => {
    // api.get đã trả JSON thẳng
    return await api.get('/api/v1/analytics/dashboard', { params })
  },

  getTrends: async (params: GetTrendsParams): Promise<TrendsResponse> => {
    // api.get đã trả JSON thẳng
    return await api.get('/api/v1/analytics/trends', { params })
  },

  getAccuracy: async () => {
    return await api.get('/api/v1/analytics/accuracy')
  },
}

export default analyticsService
