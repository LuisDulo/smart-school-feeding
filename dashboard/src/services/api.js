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
  lookup: (query) => api.get(`/meals/lookup/?q=${encodeURIComponent(query)}`),
  lookupByQR: (qrToken) => api.get(`/meals/lookup/?qr=${encodeURIComponent(qrToken)}`),
  serve: (studentId, itemIds) => api.post('/meals/serve/', { student_id: studentId, item_ids: itemIds }),
  consumption: (mealAccountId) => api.get(`/meals/consumption/${mealAccountId ? `?meal_account_id=${mealAccountId}` : ''}`),
  menuList: () => api.get('/meals/menu/'),
  menuCreate: (data) => api.post('/meals/menu/', data),
  menuUpdate: (id, data) => api.patch(`/meals/menu/${id}/`, data),
  menuDelete: (id) => api.delete(`/meals/menu/${id}/`),
  comboList: () => api.get('/meals/combos/'),
  comboCreate: (data) => api.post('/meals/combos/', data),
  comboUpdate: (id, data) => api.patch(`/meals/combos/${id}/`, data),
  comboDelete: (id) => api.delete(`/meals/combos/${id}/`),
};

export const paymentsAPI = {
  balance: () => api.get('/payments/balance/'),
  history: () => api.get('/payments/history/'),
  allBalances: () => api.get('/payments/balances/'),
  myChildren: () => api.get('/payments/my-children/'),
  creditRequestQueue: (status) => api.get(`/payments/credit-requests/queue/${status ? `?status=${status}` : ''}`),
  reviewCreditRequest: (id, data) => api.post(`/payments/credit-requests/${id}/review/`, data),
};

export const adminAPI = {
  listStudents: () => api.get('/auth/admin/students/'),
  createStudent: (data) => api.post('/auth/admin/students/', data),
  listParents: () => api.get('/auth/admin/parents/'),
  createParent: (data) => api.post('/auth/admin/parents/', data),
  linkGuardian: (data) => api.post('/auth/admin/link/', data),
  unlinkGuardian: (data) => api.delete('/auth/admin/link/', { data }),
  regenerateQR: (studentId) => api.post(`/auth/admin/students/${studentId}/regenerate-qr/`),
};

export const supportAPI = {
  queue: (status) => api.get(`/support/issues/queue/${status ? `?status=${status}` : ''}`),
  resolve: (id, data) => api.post(`/support/issues/${id}/resolve/`, data),
};

export const platformSupportAPI = {
  raiseIssue: (data) => api.post('/support/admin-issues/', data),
  myIssues: () => api.get('/support/admin-issues/'),
};

export default api;
