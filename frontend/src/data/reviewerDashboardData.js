export const reviewerProfile = {
  fullName: 'Nguyễn Minh Anh',
  email: 'minhanh.reviewer@edusuggest.vn',
  phone: '0901 234 567',
  role: 'Người kiểm duyệt',
  joinedAt: '2025-08-12',
}

export const reviewerNotifications = [
  {
    id: 'notification-1',
    title: 'Có khóa học mới cần kiểm duyệt',
    detail: 'Vue.js 3 từ cơ bản đến thực chiến',
    createdAt: '2026-11-18T08:30:00',
    read: false,
  },
  {
    id: 'notification-2',
    title: 'Tài liệu đang chờ xử lý',
    detail: 'Bộ bài tập xác suất thống kê',
    createdAt: '2026-11-17T09:25:00',
    read: false,
  },
  {
    id: 'notification-3',
    title: 'Lịch sử kiểm duyệt đã cập nhật',
    detail: 'Một nội dung đã được phê duyệt',
    createdAt: '2026-11-16T09:12:00',
    read: true,
  },
]

export const weeklyReviewStats = [
  { label: 'T2', reviewed: 5, approved: 3 },
  { label: 'T3', reviewed: 8, approved: 6 },
  { label: 'T4', reviewed: 6, approved: 4 },
  { label: 'T5', reviewed: 10, approved: 7 },
  { label: 'T6', reviewed: 7, approved: 5 },
  { label: 'T7', reviewed: 12, approved: 9 },
  { label: 'CN', reviewed: 9, approved: 6 },
]
