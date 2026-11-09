import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { File, Paths } from 'expo-file-system';

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

// Access tokens are short-lived. On a 401, trade the refresh token for a new
// pair once and retry the request. Refresh tokens rotate, so parallel 401s
// share one refresh call instead of each spending the same token. If the
// refresh fails the session is over, and AuthContext is told to log out.
let refreshing = null;
let onSessionExpired = () => {};

export function setOnSessionExpired(callback) {
  onSessionExpired = callback;
}

async function refreshTokens() {
  const refresh = await AsyncStorage.getItem('refresh_token');
  if (!refresh) throw new Error('No refresh token');
  if (!refreshing) {
    refreshing = axios.post(`${BASE_URL}/auth/token/refresh/`, { refresh }, { timeout: 10000 })
      .then(async ({ data }) => {
        await AsyncStorage.setItem('access_token', data.access);
        await AsyncStorage.setItem('refresh_token', data.refresh);
        return data.access;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

const isPublicAuthCall = (config) =>
  ['/auth/login', '/auth/register'].some((path) => (config?.url || '').startsWith(path));

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && original && !isPublicAuthCall(original)) {
      if (!original._retried) {
        original._retried = true;
        try {
          const access = await refreshTokens();
          original.headers.Authorization = `Bearer ${access}`;
          return api(original);
        } catch (refreshError) {
          // Fall through to ending the session.
        }
      }
      onSessionExpired();
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  register: (data) => api.post('/auth/register/', data),
  login: (data) => api.post('/auth/login/', data),
  profile: () => api.get('/auth/profile/'),
  logout: (refresh) => api.post('/auth/logout/', { refresh }),
  getSchools: () => api.get('/auth/schools/'),
  registerPushToken: (token, platform) => api.post('/auth/push-token/', { token, platform }),
  removePushToken: (token) => api.delete('/auth/push-token/', { data: { token } }),
};

export const paymentsAPI = {
  initiate: (data) => api.post('/payments/initiate/', data),
  status: (transactionId) => api.get(`/payments/status/${transactionId}/`),
  history: () => api.get('/payments/history/'),
  balance: (mealAccountId) => api.get(`/payments/balance/${mealAccountId ? `?meal_account_id=${mealAccountId}` : ''}`),
  myChildren: () => api.get('/payments/my-children/'),
  applyCredit: (data) => api.post('/payments/credit-requests/', data),
  myCreditRequests: () => api.get('/payments/credit-requests/'),
  monthlyReport: (months, mealAccountId) => api.get('/payments/monthly-report/', {
    params: { months: months || 3, meal_account_id: mealAccountId || undefined }
  }),
  balanceTrend: (days, mealAccountId) => api.get('/payments/balance-trend/', {
    params: { days: days || 30, meal_account_id: mealAccountId || undefined }
  }),
  activity: (mealAccountId) => api.get('/payments/activity/', {
    params: { meal_account_id: mealAccountId || undefined }
  }),
  riskScore: (mealAccountId) => api.get('/payments/risk-score/', {
    params: { meal_account_id: mealAccountId || undefined }
  }),
};

export const mealsAPI = {
  lookup: (query) => api.get(`/meals/lookup/?q=${encodeURIComponent(query)}`),
  lookupByQR: (qrToken) => api.get(`/meals/lookup/?qr=${encodeURIComponent(qrToken)}`),
  serve: (studentId, itemIds) => api.post('/meals/serve/', { student_id: studentId, item_ids: itemIds }),
  menuList: () => api.get('/meals/menu/'),
  comboList: () => api.get('/meals/combos/'),
  consumption: (mealAccountId) => api.get(`/meals/consumption/${mealAccountId ? `?meal_account_id=${mealAccountId}` : ''}`),
  qrData: (mealAccountId) => api.get('/meals/qr/', {
    params: { meal_account_id: mealAccountId || undefined }
  }),
};

export const supportAPI = {
  raiseIssue: (data) => api.post('/support/issues/', data),
  myIssues: () => api.get('/support/issues/'),
};

export default api;

// Downloads a meal report (PDF or CSV) for the selected child into the app's
// cache folder and returns the saved File. The endpoint needs the Bearer token,
// so this uses a download task with an Authorization header rather than a
// plain link. The file is checked after downloading because an HTTP error body
// (JSON) would otherwise be saved as if it were the report.
export async function downloadMealReport({ months, mealAccountId, fileFormat }) {
  // The download task bypasses axios, so make one cheap API call first: if
  // the access token has expired, the interceptor refreshes it.
  await api.get('/auth/profile/');
  const token = await AsyncStorage.getItem('access_token');
  const query = new URLSearchParams({
    months: String(months || 3),
    file_format: fileFormat,
  });
  if (mealAccountId) query.append('meal_account_id', String(mealAccountId));

  const url = `${BASE_URL}/payments/meal-report/?${query.toString()}`;
  const file = new File(Paths.cache, `meal-report-${Date.now()}.${fileFormat}`);
  const task = File.createDownloadTask(url, file, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const saved = await task.downloadAsync();

  const bytes = saved ? await saved.bytes() : null;
  const isPdf = bytes && bytes.length > 4 &&
    String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]) === '%PDF';
  const isCsv = bytes && bytes.length > 0 && bytes[0] !== 0x7b; // 0x7b is "{" (a JSON error)
  if (!(fileFormat === 'pdf' ? isPdf : isCsv)) {
    try { file.delete(); } catch (e) { /* nothing to clean up */ }
    throw new Error('The server did not return a report.');
  }
  return saved;
}
