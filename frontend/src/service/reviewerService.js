import { reactive } from 'vue'
import { REVIEWABLE_STATUSES, REVIEW_STATUS } from '@/constant/reviewStatus'
import { reviewerCourses } from '@/data/reviewerCourses'
import {
  reviewerNotifications,
  reviewerProfile,
  weeklyReviewStats,
} from '@/data/reviewerDashboardData'
import { reviewerHistory } from '@/data/reviewerHistory'
import { reviewerLectures } from '@/data/reviewerLectures'
import { reviewerMaterials } from '@/data/reviewerMaterials'

const copy = (value) => JSON.parse(JSON.stringify(value))
const courses = copy(reviewerCourses).map((course) => ({
  ...course,
  lectures: copy(reviewerLectures.filter((lecture) => lecture.courseId === course.id)),
}))

const state = reactive({
  courses,
  materials: copy(reviewerMaterials),
  history: copy(reviewerHistory),
  profile: copy(reviewerProfile),
  notifications: copy(reviewerNotifications),
})

const collections = {
  course: 'courses',
  material: 'materials',
}

const actionStatuses = {
  approve: REVIEW_STATUS.approved,
  reject: REVIEW_STATUS.rejected,
  requestChanges: REVIEW_STATUS.changesRequested,
}

function getCollection(type) {
  const collectionName = collections[type]
  if (!collectionName) {
    throw new Error(`Loại nội dung không hợp lệ: ${type}`)
  }

  return state[collectionName]
}

export function getReviewItems(type) {
  return getCollection(type)
}

export function getReviewItem(type, id) {
  const item = getCollection(type).find((record) => record.id === id)
  if (!item) {
    throw new Error('Không tìm thấy nội dung cần kiểm duyệt.')
  }

  return item
}

export function getReviewHistory() {
  return [...state.history].sort(
    (first, second) => new Date(second.reviewedAt).getTime() - new Date(first.reviewedAt).getTime(),
  )
}

export function getReviewerNotifications() {
  return state.notifications
}

export function getReviewerProfile() {
  return state.profile
}

export function saveReviewerProfile(profile) {
  if (!profile.fullName.trim() || !profile.email.trim()) {
    throw new Error('Vui lòng nhập họ tên và email.')
  }

  Object.assign(state.profile, {
    fullName: profile.fullName.trim(),
    email: profile.email.trim(),
    phone: profile.phone.trim(),
  })

  return state.profile
}

export function submitReviewDecision(type, id, action, note = '') {
  const nextStatus = actionStatuses[action]
  if (!nextStatus) {
    throw new Error('Thao tác kiểm duyệt không hợp lệ.')
  }

  const item = getReviewItem(type, id)
  if (!REVIEWABLE_STATUSES.includes(item.status)) {
    throw new Error('Nội dung này đã được xử lý và không thể kiểm duyệt lại.')
  }

  const normalizedNote = note.trim()
  if (action !== 'approve' && !normalizedNote) {
    throw new Error('Vui lòng nhập ghi chú cho thao tác này.')
  }

  item.status = nextStatus
  item.reviewNote = normalizedNote

  state.history.unshift({
    id: `history-${Date.now()}`,
    itemId: item.id,
    title: item.title,
    itemType: type,
    creator: item.creator,
    status: nextStatus,
    reviewedAt: new Date().toISOString(),
    note: normalizedNote || 'Đã phê duyệt nội dung.',
  })

  return item
}

export function getReviewerDashboardData() {
  const pendingCount = (items) =>
    items.filter((item) => REVIEWABLE_STATUSES.includes(item.status)).length
  const statusesInHistory = (status) =>
    state.history.filter((record) => record.status === status).length
  const recentlySubmitted = [...state.courses, ...state.materials]
    .filter((item) => REVIEWABLE_STATUSES.includes(item.status))
    .map((item) => ({
      ...item,
      itemType: item.documentType ? 'material' : 'course',
    }))
    .sort((first, second) => new Date(second.submittedAt) - new Date(first.submittedAt))
    .slice(0, 5)

  return {
    pendingCourses: pendingCount(state.courses),
    pendingMaterials: pendingCount(state.materials),
    approved: statusesInHistory(REVIEW_STATUS.approved),
    rejected: statusesInHistory(REVIEW_STATUS.rejected),
    recentItems: recentlySubmitted,
    notifications: state.notifications,
    weeklyStats: weeklyReviewStats,
  }
}
