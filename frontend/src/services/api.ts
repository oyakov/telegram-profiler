import axios from 'axios';

// Empty string = use page origin (works in Docker behind nginx).
// For local dev outside Docker set VITE_API_URL=http://localhost:8000 in .env.local
const API_BASE_URL = import.meta.env.VITE_API_URL ?? '';

// API key for backend authentication. Set VITE_API_KEY at build time.
// Empty = no auth header sent (local dev without API_KEY configured).
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to add auth + database headers to every request
api.interceptors.request.use((config) => {
  const selectedDb = localStorage.getItem('selected_db') || 'crm';
  config.headers['X-Database'] = selectedDb;
  if (API_KEY) {
    config.headers['Authorization'] = `Bearer ${API_KEY}`;
  }
  return config;
});

// Interceptor to handle 401 responses — only redirect if not already on /login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

export const fetcher = (url: string) => api.get(url).then(res => res.data);

export const setDatabase = (db: string) => {
  localStorage.setItem('selected_db', db);
  window.dispatchEvent(new Event('storage')); // Trigger update in components
};

export const getDatabase = () => {
  return localStorage.getItem('selected_db') || 'crm';
};
