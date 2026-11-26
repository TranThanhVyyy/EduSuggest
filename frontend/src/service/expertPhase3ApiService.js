import api from '@/service/api'
import { extractApiError } from '@/service/notificationApiService'

export { extractApiError }

// =====================================================================
// EXPERT Profile
// =====================================================================
export async function fetchMyExpertProfile() {
  const { data } = await api.get('/expert/profile')
  return data
}

// =====================================================================
// EXPERT Assignments (GĐ3.3 Lifecycle)
// =====================================================================
export async function fetchMyAssignments({ status = '', targetType = '', limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (targetType) params.target_type = targetType
  const { data } = await api.get('/expert/assignments', { params })
  return data
}

export async function fetchMyAssignmentDetail(assignmentId) {
  const { data } = await api.get(`/expert/assignments/${assignmentId}`)
  return data
}

export async function acceptMyAssignment(assignmentId) {
  const { data } = await api.post(`/expert/assignments/${assignmentId}/accept`)
  return data
}

export async function declineMyAssignment(assignmentId, { maLyDoTuChoi, lyDoTuChoi }) {
  const { data } = await api.post(`/expert/assignments/${assignmentId}/decline`, {
    maLyDoTuChoi,
    lyDoTuChoi,
  })
  return data
}

export async function startMyAssignment(assignmentId) {
  const { data } = await api.post(`/expert/assignments/${assignmentId}/start`)
  return data
}

export async function saveMyAssignmentDraft(assignmentId, banNhapDanhGia) {
  const { data } = await api.put(`/expert/assignments/${assignmentId}/draft`, { banNhapDanhGia })
  return data
}

export async function submitMyAssignmentDecision(assignmentId, payload) {
  const { data } = await api.post(`/expert/assignments/${assignmentId}/decision`, payload)
  return data
}

// =====================================================================
// EXPERT Accountability (Read-only Own Data)
// =====================================================================
export async function fetchMyAccountabilitySummary() {
  const { data } = await api.get('/expert/accountability/summary')
  return data
}

export async function fetchMyViolations({ status = '', cycle = null, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (cycle) params.cycle = cycle
  const { data } = await api.get('/expert/accountability/violations', { params })
  return data
}

export async function fetchAccountabilityPolicy() {
  const { data } = await api.get('/expert/accountability/policy')
  return data
}

// =====================================================================
// EXPERT Availability (YeuCauTamNgungChuyenGia)
// =====================================================================
export async function fetchMyAvailabilityRequests({ status = '', limit = 50, offset = 0 } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  const { data } = await api.get('/expert/availability', { params })
  return data
}

export async function createMyAvailabilityRequest({ ngayBatDau, ngayKetThuc, lyDo }) {
  const { data } = await api.post('/expert/availability', { ngayBatDau, ngayKetThuc, lyDo })
  return data
}

export async function cancelMyAvailabilityRequest(requestId, lyDoHuy) {
  const { data } = await api.post(`/expert/availability/${requestId}/cancel`, { lyDoHuy })
  return data
}

// =====================================================================
// Countdown & Constants
// =====================================================================
export const DECLINE_REASON_OPTIONS = [
  { code: 'WORKLOAD_PERSONAL', label: 'Bận việc cá nhân / quá tải (tính vi phạm tự động)', autoViolation: true },
  { code: 'CONFLICT_OF_INTEREST', label: 'Xung đột lợi ích (chờ ADMIN xem xét)', autoViolation: false },
  { code: 'SYSTEM_MISASSIGNMENT', label: 'Hệ thống phân công sai chuyên môn (chờ ADMIN xem xét)', autoViolation: false },
  { code: 'TECHNICAL_ISSUE', label: 'Sự cố kỹ thuật / không mở được nội dung (chờ ADMIN xem xét)', autoViolation: false },
  { code: 'OTHER', label: 'Lý do khác (chờ ADMIN xem xét)', autoViolation: false },
]

export function formatRemainingTime(deadlineIso, nowMs = Date.now()) {
  if (!deadlineIso) return '—'
  const raw = typeof deadlineIso === 'string' && !/[zZ]|[+-]\d{2}:\d{2}$/.test(deadlineIso) ? `${deadlineIso}Z` : deadlineIso
  const diff = new Date(raw).getTime() - nowMs
  if (!Number.isFinite(diff)) return '—'
  if (diff <= 0) return 'Đã quá hạn'
  const totalMinutes = Math.floor(diff / 60000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    return `Còn ${days} ngày ${hours % 24} giờ`
  }
  return `Còn ${hours} giờ ${minutes} phút`
}
