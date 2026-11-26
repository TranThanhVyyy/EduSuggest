import api from '@/service/api'
import { extractApiError } from '@/service/notificationApiService'

export { extractApiError }

// =====================================================================
// Overview & System Configuration (CauHinhPhanCong)
// =====================================================================
export async function fetchExpertOverview() {
  const { data } = await api.get('/admin/assignments/overview')
  return data
}

export async function fetchAssignmentConfig() {
  const { data } = await api.get('/admin/assignments/config')
  return data
}

export async function updateAssignmentConfig(payload) {
  const { data } = await api.patch('/admin/assignments/config', payload)
  return data
}

// =====================================================================
// Assignments, Workload & Durable Queue
// =====================================================================
export async function fetchAdminAssignments({ status = '', targetType = '', expertId = null, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (targetType) params.target_type = targetType
  if (expertId) params.expert_id = expertId
  const { data } = await api.get('/admin/assignments', { params })
  return data
}

export async function fetchAdminAssignmentDetail(assignmentId) {
  const { data } = await api.get(`/admin/assignments/${assignmentId}`)
  return data
}

export async function cancelAdminAssignment(assignmentId, { lyDoHuy, requeue = true }) {
  const { data } = await api.post(`/admin/assignments/${assignmentId}/cancel`, { lyDoHuy, requeue })
  return data
}

export async function manualAssignExpert({ loaiDoiTuong, maDoiTuong, maChuyenGia, lyDoPhanCong }) {
  const { data } = await api.post('/admin/assignments/manual', {
    loaiDoiTuong,
    maDoiTuong: Number(maDoiTuong),
    maChuyenGia: Number(maChuyenGia),
    lyDoPhanCong,
  })
  return data
}

export async function fetchAdminQueueJobs({ status = '', targetType = '', limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (targetType) params.target_type = targetType
  const { data } = await api.get('/admin/assignments/queue', { params })
  return data
}

export async function retryAdminQueueJob(jobId) {
  const { data } = await api.post(`/admin/assignments/queue/${jobId}/retry`)
  return data
}

export async function fetchAdminWorkload() {
  const { data } = await api.get('/admin/assignments/workload')
  return data
}

// =====================================================================
// Accountability, Violations, Lock/Unlock & Audit Logs
// =====================================================================
export async function fetchAccountabilityExperts() {
  const { data } = await api.get('/admin/accountability/experts')
  return data
}

export async function fetchAccountabilityExpertDetail(expertId) {
  const { data } = await api.get(`/admin/accountability/experts/${expertId}`)
  return data
}

export async function lockExpertAccount(expertId, lyDo) {
  const { data } = await api.post(`/admin/accountability/experts/${expertId}/lock`, { lyDo })
  return data
}

export async function unlockExpertAccount(expertId, lyDo) {
  const { data } = await api.post(`/admin/accountability/experts/${expertId}/unlock`, { lyDo })
  return data
}

export async function fetchAccountabilityViolations({ expertId = null, status = '', cycle = null, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (expertId) params.expert_id = expertId
  if (status) params.status = status
  if (cycle) params.cycle = cycle
  const { data } = await api.get('/admin/accountability/violations', { params })
  return data
}

export async function confirmViolation(violationId, ghiChuXuLy) {
  const { data } = await api.post(`/admin/accountability/violations/${violationId}/confirm`, { ghiChuXuLy })
  return data
}

export async function exemptViolation(violationId, ghiChuXuLy) {
  const { data } = await api.post(`/admin/accountability/violations/${violationId}/exempt`, { ghiChuXuLy })
  return data
}

export async function fetchAccountabilityAuditLogs({ expertId = null, action = '', cycle = null, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (expertId) params.expert_id = expertId
  if (action) params.action = action
  if (cycle) params.cycle = cycle
  const { data } = await api.get('/admin/accountability/audit-logs', { params })
  return data
}

// =====================================================================
// Expert Availability Management (YeuCauTamNgungChuyenGia)
// =====================================================================
export async function fetchAdminAvailabilityRequests({ status = '', expertId = null, activeNow = false, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (expertId) params.expert_id = expertId
  if (activeNow) params.active_now = true
  const { data } = await api.get('/admin/availability', { params })
  return data
}

export async function approveAvailabilityRequest(requestId, ghiChuXuLy = '') {
  const body = ghiChuXuLy?.trim() ? { ghiChuXuLy: ghiChuXuLy.trim() } : {}
  const { data } = await api.post(`/admin/availability/${requestId}/approve`, body)
  return data
}

export async function rejectAvailabilityRequest(requestId, ghiChuXuLy) {
  const { data } = await api.post(`/admin/availability/${requestId}/reject`, { ghiChuXuLy })
  return data
}

export async function revokeAvailabilityRequest(requestId, lyDoHuy) {
  const { data } = await api.post(`/admin/availability/${requestId}/revoke`, { lyDoHuy })
  return data
}

// =====================================================================
// Formatting Helpers
// =====================================================================
export function formatDateTimeVi(value) {
  if (!value) return '—'
  const raw = typeof value === 'string' && !/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? `${value}Z` : value
  const dt = new Date(raw)
  if (Number.isNaN(dt.getTime())) return String(value)
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(dt)
}
