import api from './api';

const analyticsService = {
  // Get dashboard data
  getDashboard: async () => {
    return await api.get('/api/v1/analytics/dashboard');
  },

  // Get trends
  getTrends: async (params = {}) => {
    return await api.get('/api/v1/analytics/trends', { params });
  },

  // Get model accuracy
  getAccuracy: async () => {
    return await api.get('/api/v1/analytics/accuracy');
  },

  // Get product performance
  getProductPerformance: async (productId, params = {}) => {
    return await api.get(`/api/v1/analytics/products/${productId}/performance`, { params });
  },

  // Get recommendations
  getRecommendations: async () => {
    return await api.get('/api/v1/optimize/recommendations');
  },
};

export default analyticsService;
