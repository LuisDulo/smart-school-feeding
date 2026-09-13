import axios from 'axios';

const BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/';
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  login: (data) => api.post('/auth/login/', data),
  profile: () => api.get('/auth/profile/'),
};

export const forecastAPI = {
  generate: () => api.post('/forecast/generate/'),
  history: () => api.get('/forecast/history/'),
  stats: () => api.get('/forecast/stats/'),
};

export const mealsAPI = {
  log: (dateStr) => api.get(`/meals/log/${dateStr ? `?date=${dateStr}` : ''}`),
  lookup: (query) => api.get(`/meals/lookup/?q=${query}`),
  serve: (studentId) => api.post('/meals/serve/', { student_id: studentId }),
};

export const paymentsAPI = {
  balance: () => api.get('/payments/balance/'),
  history: () => api.get('/payments/history/'),
  allBalances: () => api.get('/payments/balances/'),
};

export default api;
