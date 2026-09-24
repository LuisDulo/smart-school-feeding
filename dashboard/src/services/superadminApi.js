import api from './api';

export const superAdminAPI = {
  overview:     ()         => api.get('/superadmin/overview/'),
  schools:      ()         => api.get('/superadmin/schools/'),
  schoolDetail: (id)       => api.get(`/superadmin/schools/${id}/`),
  createSchool: (data)     => api.post('/superadmin/schools/', data),
  students:     (params)   => api.get('/superadmin/students/', { params }),
  staff:        (params)   => api.get('/superadmin/staff/', { params }),
  createStaff:  (data)     => api.post('/superadmin/staff/', data),
  anomalies:    (params)   => api.get('/superadmin/anomalies/', { params }),
  analytics:    ()         => api.get('/superadmin/analytics/'),
  reportCSV:    (type)     => api.get(`/superadmin/reports/${type}/`, {
                               responseType: 'blob' }),
  reportSummary: ()        => api.get('/superadmin/reports/summary/'),
  adminIssues:  (status)   => api.get(`/support/admin-issues/queue/${status ? `?status=${status}` : ''}`),
  resolveAdminIssue: (id, data) => api.post(`/support/admin-issues/${id}/resolve/`, data),
};
