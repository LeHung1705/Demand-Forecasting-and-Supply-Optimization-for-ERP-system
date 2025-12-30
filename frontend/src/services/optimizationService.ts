// src/services/optimizationService.ts
import api from './api'

export type OptimizeSupplyPayload = {
  time_range: '7d' | '30d' | '90d'
  store_id?: number
  product_ids?: number[]
  constraints: {
    budget: number
    max_inventory: number
    lead_time: number
  }
}

export const optimizationService = {
  runSupplyOptimization: async (payload: OptimizeSupplyPayload) => {
    return await api.post('/api/v1/optimize/supply', payload)
  },

  getRecommendations: async (params: { time_range?: string; store_id?: number; top_n?: number } = {}) => {
    return await api.get('/api/v1/optimize/recommendations', { params })
  },

  generateReport: async (payload: OptimizeSupplyPayload) => {
    // Return blob for file download
    return await api.post('/api/v1/optimize/report', payload, {
      responseType: 'blob'
    })
  },
}
