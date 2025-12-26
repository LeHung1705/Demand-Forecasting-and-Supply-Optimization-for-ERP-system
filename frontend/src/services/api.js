import axios from 'axios';

/**
 * Typed axios instance that already unwraps `response.data`.
 * @typedef {import('axios').AxiosRequestConfig} AxiosRequestConfig
 * @typedef {import('axios').AxiosInstance & {
 *   get<T = any, R = T>(url: string, config?: AxiosRequestConfig): Promise<R>;
 *   post<T = any, R = T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<R>;
 *   put<T = any, R = T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<R>;
 *   delete<T = any, R = T>(url: string, config?: AxiosRequestConfig): Promise<R>;
 * }} ApiInstance
 */

/** @type {ApiInstance} */
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
);

export default api;
