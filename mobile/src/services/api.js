import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// This must be your development machine's local IPv4 address on the same
// WiFi network as your phone (a physical phone/emulator can't reach
// "localhost" — that would mean itself, not your laptop).
// Find it by running: ipconfig (Windows) — look for the WiFi adapter's
// IPv4 Address. Update this if you switch networks.
const BASE_URL = 'http://192.168.0.44:8000/api';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach token to every request automatically
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (data) => api.post('/auth/register/', data),
  login: (data) => api.post('/auth/login/', data),
  profile: () => api.get('/auth/profile/'),
  logout: () => api.post('/auth/logout/'),
  getSchools: () => api.get('/auth/schools/'),
};

export const paymentsAPI = {
  initiate: (data) => api.post('/payments/initiate/', data),
  status: (transactionId) => api.get(`/payments/status/${transactionId}/`),
  history: () => api.get('/payments/history/'),
  balance: (mealAccountId) => api.get(`/payments/balance/${mealAccountId ? `?meal_account_id=${mealAccountId}` : ''}`),
  myChildren: () => api.get('/payments/my-children/'),
  applyCredit: (data) => api.post('/payments/credit-requests/', data),
  myCreditRequests: () => api.get('/payments/credit-requests/'),
};

export const mealsAPI = {
  lookup: (query) => api.get(`/meals/lookup/?q=${encodeURIComponent(query)}`),
  serve: (studentId, itemIds) => api.post('/meals/serve/', { student_id: studentId, item_ids: itemIds }),
  menuList: () => api.get('/meals/menu/'),
  comboList: () => api.get('/meals/combos/'),
  consumption: (mealAccountId) => api.get(`/meals/consumption/${mealAccountId ? `?meal_account_id=${mealAccountId}` : ''}`),
};

export const supportAPI = {
  raiseIssue: (data) => api.post('/support/issues/', data),
  myIssues: () => api.get('/support/issues/'),
};

export default api;
