import api from '@/service/api'

export function extractApiError(error, fallback = 'Không thể kết nối máy chủ. Vui lòng thử lại.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first?.msg) return first.msg
  }
  return error?.message || fallback
}

export async function fetchNotifications({ isRead = null, limit = 20, offset = 0 } = {}) {
  const params = { limit, offset }
  if (isRead !== null && isRead !== undefined) {
    params.is_read = isRead
  }
  const { data } = await api.get('/notifications', { params })
  return data
}

export async function fetchUnreadNotificationCount() {
  const { data } = await api.get('/notifications/unread-count')
  return Number(data?.unreadCount || 0)
}

export async function markNotificationRead(notificationId) {
  const { data } = await api.post(`/notifications/${notificationId}/read`)
  return data
}

export async function markAllNotificationsRead() {
  const { data } = await api.post('/notifications/read-all')
  return Number(data?.updatedCount || 0)
}
