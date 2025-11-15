// API Endpoints
export const API_ENDPOINTS = {
  PRODUCTS: '/api/v1/products',
  FORECASTS: '/api/v1/forecasts',
  ANALYTICS: '/api/v1/analytics',
  OPTIMIZE: '/api/v1/optimize',
};

// App Configuration
export const APP_CONFIG = {
  NAME: process.env.REACT_APP_NAME || 'Demand Forecasting',
  VERSION: process.env.REACT_APP_VERSION || '1.0.0',
  API_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
};

// Forecast Models
export const FORECAST_MODELS = {
  ODOO_BASIC: 'odoo_basic',
  ODOO_SOTA: 'odoo_sota',
  SAP_BASIC: 'sap_basic',
  SAP_SOTA: 'sap_sota',
};

export const MODEL_LABELS = {
  [FORECAST_MODELS.ODOO_BASIC]: 'ODOO Basic',
  [FORECAST_MODELS.ODOO_SOTA]: 'ODOO SOTA',
  [FORECAST_MODELS.SAP_BASIC]: 'SAP Basic',
  [FORECAST_MODELS.SAP_SOTA]: 'SAP SOTA',
};

// Time horizons
export const FORECAST_HORIZONS = [
  { value: 7, label: '7 ngày' },
  { value: 14, label: '14 ngày' },
  { value: 30, label: '30 ngày' },
  { value: 60, label: '60 ngày' },
  { value: 90, label: '90 ngày' },
];

// Chart colors
export const CHART_COLORS = {
  primary: '#1976d2',
  secondary: '#dc004e',
  success: '#4caf50',
  warning: '#ff9800',
  error: '#f44336',
  info: '#2196f3',
};

// Status colors
export const STATUS_COLORS = {
  active: '#4caf50',
  inactive: '#9e9e9e',
  pending: '#ff9800',
  error: '#f44336',
};

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [10, 25, 50, 100],
};
