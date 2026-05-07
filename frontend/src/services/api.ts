import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to add the database header from localStorage
api.interceptors.request.use((config) => {
  const selectedDb = localStorage.getItem('selected_db') || 'crm';
  config.headers['X-Database'] = selectedDb;
  return config;
});

export default api;

export const setDatabase = (db: string) => {
  localStorage.setItem('selected_db', db);
  window.dispatchEvent(new Event('storage')); // Trigger update in components
};

export const getDatabase = () => {
  return localStorage.getItem('selected_db') || 'crm';
};
