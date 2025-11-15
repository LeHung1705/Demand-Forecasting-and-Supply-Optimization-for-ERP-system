import api from './api';

const productService = {
  // Get all products
  getAll: async (params = {}) => {
    return await api.get('/api/v1/products', { params });
  },

  // Get product by ID
  getById: async (id) => {
    return await api.get(`/api/v1/products/${id}`);
  },

  // Create new product
  create: async (productData) => {
    return await api.post('/api/v1/products', productData);
  },

  // Update product
  update: async (id, productData) => {
    return await api.put(`/api/v1/products/${id}`, productData);
  },

  // Delete product
  delete: async (id) => {
    return await api.delete(`/api/v1/products/${id}`);
  },

  // Get product statistics
  getStats: async (id) => {
    return await api.get(`/api/v1/products/${id}/stats`);
  },
};

export default productService;
