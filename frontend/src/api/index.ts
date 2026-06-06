import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    try {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (e) {
      console.warn('[API] Failed to access localStorage for token:', e)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response?.status === 401) {
      try {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      } catch (e) {
        console.warn('[API] Failed to clear localStorage:', e)
      }
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),

  register: (data: any) => api.post('/auth/register', data),

  getCurrentUser: () => api.get('/auth/me'),

  listUsers: () => api.get('/auth/users'),

  updateUser: (id: number, data: any) => api.put(`/auth/users/${id}`, data),

  deleteUser: (id: number) => api.delete(`/auth/users/${id}`),

  toggleUserStatus: (id: number) => api.patch(`/auth/users/${id}/status`),

  resetPassword: (id: number, newPassword: string) =>
    api.post(`/auth/users/${id}/reset-password`, { new_password: newPassword })
}

export const simulationAPI = {
  list: (params?: any) => api.get('/simulations', { params }),

  get: (id: number) => api.get(`/simulations/${id}`),

  create: (data: any) => api.post('/simulations', data),

  update: (id: number, data: any) => api.put(`/simulations/${id}`, data),

  delete: (id: number) => api.delete(`/simulations/${id}`),

  uploadParams: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/simulations/upload-params', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  start: (id: number, maxIterations?: number) =>
    api.post(`/simulations/${id}/start`, null, { params: { maxIterations } }),

  step: (id: number, nSteps: number = 1) =>
    api.post(`/simulations/${id}/step`, null, { params: { n_steps: nSteps } }),

  verify: (id: number, approved: boolean, comments?: string) =>
    api.post(`/simulations/${id}/verify`, null, { params: { approved, comments } }),

  restartAdjusted: (id: number) => api.post(`/simulations/${id}/restart-adjusted`),

  getTimeSeries: (id: number, params?: any) =>
    api.get(`/simulations/${id}/time-series`, { params }),

  getPolarityReversals: (id: number) =>
    api.get(`/simulations/${id}/polarity-reversals`),

  getAdjustmentLogs: (id: number) =>
    api.get(`/simulations/${id}/adjustment-logs`),

  getGroupStatus: () => api.get('/simulations/group-status'),

  resumeGroup: (groupName: string) => api.post(`/simulations/group/${groupName}/resume`)
}

export const monitoringAPI = {
  getAlerts: (params?: any) => api.get('/monitoring/alerts', { params }),

  getUnreadCount: () => api.get('/monitoring/alerts/unread-count'),

  markRead: (id: number) => api.put(`/monitoring/alerts/${id}/read`),

  markReviewed: (id: number) => api.post(`/monitoring/alerts/${id}/review`),

  deleteAlert: (id: number) => api.delete(`/monitoring/alerts/${id}`),

  createReview: (data: any) => api.post('/monitoring/reviews', data),

  getSimulationReviews: (id: number) =>
    api.get(`/monitoring/simulations/${id}/reviews`),

  getSimulationAdjustments: (id: number) =>
    api.get(`/monitoring/simulations/${id}/adjustments`)
}

export const reportsAPI = {
  generateReport: (id: number) => api.post(`/reports/${id}/generate`),

  downloadReport: (id: number) =>
    api.get(`/reports/${id}/download`, { responseType: 'blob' }),

  exportFields: (id: number, params?: any) =>
    api.get(`/reports/${id}/export/fields`, { params, responseType: 'blob' }),

  exportTimeSeries: (id: number, params?: any) =>
    api.get(`/reports/${id}/export/time-series`, { params, responseType: 'blob' }),

  exportParameters: (id: number, params?: any) =>
    api.get(`/reports/${id}/export/parameters`, { params, responseType: 'blob' }),

  getRecommendation: (data: any, topK: number = 5) =>
    api.post('/reports/recommendations', data, { params: { top_k: topK } }),

  listRecommendations: (limit: number = 10) =>
    api.get('/reports/recommendations', { params: { limit } }),

  getModelInfo: () => api.get('/reports/recommendations/model-info'),

  trainModel: () => api.post('/reports/recommendations/train')
}

export const approvalAPI = {
  submitForApproval: (id: number) => api.post(`/simulations/${id}/submit-approval`),

  getPendingPostdoc: () => api.get('/approvals/pending-postdoc'),

  getPendingProfessor: () => api.get('/approvals/pending-professor'),

  postdocApprove: (id: number, approved: boolean, comments?: string) =>
    api.post(`/approvals/${id}/postdoc`, null, { params: { approved, comments } }),

  professorApprove: (id: number, approved: boolean, comments?: string) =>
    api.post(`/approvals/${id}/professor`, null, { params: { approved, comments } }),

  getSimulationApprovals: (id: number) =>
    api.get(`/approvals/simulation/${id}`),

  getMyApprovals: () => api.get('/approvals/my-approvals'),

  generateDailyStats: () => api.get('/statistics/daily/generate'),

  getDailyStats: (days: number = 30) =>
    api.get('/statistics/daily', { params: { days } }),

  getOverview: () => api.get('/statistics/overview'),

  getDashboard: (days: number = 30) =>
    api.get('/statistics/dashboard', { params: { days } }),

  getHeatmap: (days: number = 30) =>
    api.get('/statistics/heatmap', { params: { days } }),

  generateAnimation: (id: number, params?: any) =>
    api.post(`/statistics/${id}/animation`, null, { params }),

  getGroupFailures: () => api.get('/statistics/group-failures')
}
