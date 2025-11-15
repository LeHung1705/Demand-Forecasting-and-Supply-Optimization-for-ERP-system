import api from './api';

const forecastService = {
  // Predict demand
  predict: async (forecastData) => {
    return await api.post('/api/v1/forecasts/predict', forecastData);
  },

  // Get all forecasts
  getAll: async (params = {}) => {
    return await api.get('/api/v1/forecasts', { params });
  },

  // Get forecast by ID
  getById: async (id) => {
    return await api.get(`/api/v1/forecasts/${id}`);
  },

  // Get forecast for specific product
  getByProduct: async (productId, params = {}) => {
    return await api.get(`/api/v1/forecasts/product/${productId}`, { params });
  },

  // Get model accuracy
  getAccuracy: async (modelName) => {
    return await api.get('/api/v1/analytics/accuracy', {
      params: { model: modelName },
    });
  },
};

export default forecastService;
