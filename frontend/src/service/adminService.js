import { reactive } from 'vue'
import { REVIEWABLE_STATUSES, REVIEW_STATUS } from '@/constant/reviewStatus'
import {
  ADMIN_ROLES,
  adminCategories,
  adminCourses,
  adminLessons,
  adminMaterials,
  adminProfile,
  adminProviders,
  adminReviewers,
  adminUsers,
  analyticsByPeriod,
  recommendationMetrics,
} from '@/data/adminData'
import { getReviewHistory, getReviewItems } from '@/service/reviewerService'

const copy = (value) => JSON.parse(JSON.stringify(value))
const assignmentByItem = reactive({})

const state = reactive({
  users: copy(adminUsers),
  reviewers: copy(adminReviewers),
  providers: copy(adminProviders),
  categories: copy(adminCategories),
  courses: copy(adminCourses),
  lessons: copy(adminLessons),
  materials: copy(adminMaterials),
  profile: copy(adminProfile),
})

const resourceCollections = {
  users: 'users',
  reviewers: 'reviewers',
  providers: 'providers',
  categories: 'categories',
  courses: 'courses',
  lessons: 'lessons',
  materials: 'materials',
}

function getCollection(resource) {
  const collectionName = resourceCollections[resource]
  if (!collectionName) throw new Error(`Danh mục quản trị không hợp lệ: ${resource}`)
  return state[collectionName]
}

function reviewerNameFor(itemId) {
  const reviewerId = assignmentByItem[itemId]?.reviewerId
  return state.reviewers.find((reviewer) => reviewer.id === reviewerId)?.fullName || ''
}

function getReviewItemCategory(item, itemType) {
  if (itemType === 'material' && item.relatedCourse) {
    const relatedCourse = getReviewItems('course').find(
      (course) => course.id === item.relatedCourse || course.title === item.relatedCourse,
    )
    if (relatedCourse?.category) return relatedCourse.category
  }

  return item.category || ''
}

function normalizeExpertise(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLocaleLowerCase('vi')
}

function reviewerMatchesCategory(reviewer, category) {
  const normalizedCategory = normalizeExpertise(category)
  if (!normalizedCategory) return false

  return String(reviewer.expertise || '')
    .split(/[,;|/]/)
    .some((specialty) => normalizeExpertise(specialty) === normalizedCategory)
}

export function getAdminRows(resource) {
  if (resource === 'review-monitor') return getAdminReviewMonitor()
  if (resource === 'users') {
    return getCollection(resource).filter((user) => user.role === ADMIN_ROLES.user)
  }
  return getCollection(resource)
}

export function getAdminRecord(resource, id) {
  const record = getCollection(resource).find((item) => item.id === id)
  if (!record) throw new Error('Không tìm thấy dữ liệu cần xem.')

  if (resource === 'courses') {
    return {
      ...record,
      lessons: state.lessons.filter((lesson) => lesson.courseId === record.id),
      materials: state.materials.filter((material) => material.courseId === record.id),
    }
  }

  if (resource === 'lessons') {
    return {
      ...record,
      course: state.courses.find((course) => course.id === record.courseId) || null,
      materials: state.materials.filter((material) => material.lessonId === record.id),
    }
  }

  return record
}

export function getAdminCourseLessons(courseId) {
  return state.lessons
    .filter((lesson) => lesson.courseId === courseId && lesson.reviewStatus === REVIEW_STATUS.approved)
    .sort((first, second) => first.order - second.order)
}

export function saveAdminRecord(resource, values) {
  if (['courses', 'lessons', 'materials'].includes(resource)) {
    throw new Error('Admin chỉ được xem nội dung đã duyệt, không được tạo hoặc chỉnh sửa nội dung.')
  }

  const collection = getCollection(resource)
  const existing = values.id ? collection.find((record) => record.id === values.id) : null
  const normalized = { ...values }
  if (resource === 'users') {
    if (existing && existing.role !== ADMIN_ROLES.user) {
      throw new Error('Chỉ tài khoản User được chỉnh sửa tại màn hình Tài khoản.')
    }
    if (normalized.role && normalized.role !== ADMIN_ROLES.user) {
      throw new Error('Mục Tài khoản chỉ hỗ trợ tài khoản User.')
    }
    normalized.role = ADMIN_ROLES.user
  }

  if (existing) {
    Object.assign(existing, normalized)
    return existing
  }

  normalized.id ||= `${resource.slice(0, 3).toUpperCase()}-${Date.now()}`
  normalized.status ||= 'active'
  collection.unshift(normalized)
  return normalized
}

export function toggleAdminAccount(resource, id) {
  if (!['users', 'reviewers', 'providers'].includes(resource)) {
    throw new Error('Chỉ tài khoản người dùng, Reviewer hoặc Provider mới có thể khóa/mở khóa.')
  }

  const record = getCollection(resource).find((item) => item.id === id)
  if (!record) throw new Error('Không tìm thấy tài khoản.')
  if (resource === 'users' && record.role !== ADMIN_ROLES.user) {
    throw new Error('Chỉ tài khoản User được thay đổi trạng thái tại màn hình Tài khoản.')
  }

  if (record.role === ADMIN_ROLES.admin && record.status === 'active') {
    const activeAdmins = state.users.filter(
      (user) => user.role === ADMIN_ROLES.admin && user.status === 'active',
    )
    if (activeAdmins.length <= 1) {
      throw new Error('Không thể khóa tài khoản Admin cuối cùng đang hoạt động.')
    }
  }

  record.status = record.status === 'active' ? 'locked' : 'active'
  return record
}

export function deleteAdminCategory(id) {
  const category = state.categories.find((item) => item.id === id)
  if (!category) throw new Error('Không tìm thấy danh mục.')
  if (category.courseCount > 0) {
    throw new Error('Không thể xóa danh mục đang có khóa học liên quan.')
  }

  state.categories = state.categories.filter((item) => item.id !== id)
}

export function getAdminReviewRequests() {
  return [
    ...getReviewItems('course').map((item) => ({ ...item, itemType: 'course' })),
    ...getReviewItems('material').map((item) => ({ ...item, itemType: 'material' })),
  ]
    .filter((item) => REVIEWABLE_STATUSES.includes(item.status))
    .map((item) => ({
      ...item,
      category: getReviewItemCategory(item, item.itemType),
      assignedReviewerId: assignmentByItem[item.id]?.reviewerId || '',
      reviewerName: reviewerNameFor(item.id),
      assignedAt: assignmentByItem[item.id]?.assignedAt || '',
    }))
}

export function getAdminReviewMonitor() {
  const history = getReviewHistory()
  const latestHistoryByItem = new Map()
  for (const record of history) {
    const key = `${record.itemType || 'course'}:${record.itemId}`
    if (!latestHistoryByItem.has(key)) latestHistoryByItem.set(key, record)
  }

  const currentItems = [
    ...getReviewItems('course').map((item) => ({ ...item, itemType: 'course' })),
    ...getReviewItems('material').map((item) => ({ ...item, itemType: 'material' })),
  ]
  const currentItemKeys = new Set(currentItems.map((item) => `${item.itemType}:${item.id}`))
  const submissions = currentItems.map((item) => {
    const latestReview = latestHistoryByItem.get(`${item.itemType}:${item.id}`)
    return {
      ...item,
      reviewerName: reviewerNameFor(item.id) || 'Chưa phân công',
      assignedAt: assignmentByItem[item.id]?.assignedAt || '',
      completedAt: latestReview?.reviewedAt || '',
      note: item.reviewNote || latestReview?.note || '',
    }
  })

  const standaloneHistory = history
    .filter((record) => !currentItemKeys.has(`${record.itemType || 'course'}:${record.itemId}`))
    .map((record) => ({
      ...record,
      itemType: record.itemType || 'course',
      reviewerName: reviewerNameFor(record.itemId) || 'Chưa có dữ liệu',
      completedAt: record.reviewedAt,
      note: record.note || '',
    }))

  return [...standaloneHistory, ...submissions]
}

export function assignAdminReviewer(itemId, reviewerId) {
  const reviewer = state.reviewers.find((record) => record.id === reviewerId)
  if (!reviewer || reviewer.status !== 'active') {
    throw new Error('Vui lòng chọn Reviewer đang hoạt động.')
  }

  const item = [...getReviewItems('course'), ...getReviewItems('material')]
    .find((record) => record.id === itemId)
  if (!item || !REVIEWABLE_STATUSES.includes(item.status)) {
    throw new Error('Nội dung không còn trong danh sách cần phân công.')
  }

  if (assignmentByItem[itemId]?.reviewerId === reviewerId) return item

  assignmentByItem[itemId] = {
    reviewerId,
    assignedAt: new Date().toISOString(),
  }

  return item
}

export function autoAssignAdminReviewers() {
  const unassignedRequests = getAdminReviewRequests()
    .filter((request) => !request.assignedReviewerId)
    .sort((first, second) => String(first.submittedAt || '').localeCompare(String(second.submittedAt || '')))
  const assigned = []
  const unassigned = []
  const workloads = new Map(
    state.reviewers.map((reviewer) => [reviewer.id, getAdminReviewerWorkload(reviewer.id)]),
  )

  for (const request of unassignedRequests) {
    const category = request.category
    const eligibleReviewers = state.reviewers
      .filter((reviewer) => reviewer.status === 'active' && reviewerMatchesCategory(reviewer, category))
      .sort((first, second) => workloads.get(first.id) - workloads.get(second.id))
    const reviewer = eligibleReviewers[0]

    if (!reviewer) {
      unassigned.push({
        itemId: request.id,
        title: request.title,
        category,
        reason: category ? 'Không có Reviewer đang hoạt động phù hợp chuyên môn.' : 'Nội dung chưa có danh mục.',
      })
      continue
    }

    assignAdminReviewer(request.id, reviewer.id)
    workloads.set(reviewer.id, workloads.get(reviewer.id) + 1)
    assigned.push({
      itemId: request.id,
      title: request.title,
      category,
      reviewerId: reviewer.id,
      reviewerName: reviewer.fullName,
    })
  }

  return { assigned, unassigned }
}

export function getAdminReviewerWorkload(reviewerId) {
  const reviewer = state.reviewers.find((record) => record.id === reviewerId)
  if (!reviewer) return 0

  const reviewableItemIds = new Set(
    getAdminReviewRequests().map((request) => request.id),
  )
  const sessionAssignments = Object.entries(assignmentByItem)
    .filter(([itemId, assignment]) => assignment.reviewerId === reviewerId && reviewableItemIds.has(itemId))
    .length
  return reviewer.activeAssignments + sessionAssignments
}

export function getAdminVisibilityItems() {
  return [
    ...state.courses.map((item) => ({ ...item, itemType: 'course', displayName: item.title })),
    ...state.lessons.map((item) => ({
      ...item,
      providerName: state.courses.find((course) => course.id === item.courseId)?.providerName || '',
      itemType: 'lesson',
      displayName: item.title,
    })),
    ...state.materials.map((item) => ({ ...item, itemType: 'material', displayName: item.title })),
  ].filter((item) => item.reviewStatus === REVIEW_STATUS.approved)
}

export function setAdminVisibility(itemType, id, visibility) {
  if (!['visible', 'hidden'].includes(visibility)) {
    throw new Error('Trạng thái hiển thị không hợp lệ.')
  }

  const resource = { course: 'courses', lesson: 'lessons', material: 'materials' }[itemType]
  if (!resource) throw new Error('Loại nội dung không hợp lệ.')

  const item = state[resource].find((record) => record.id === id)
  if (!item || item.reviewStatus !== REVIEW_STATUS.approved) {
    throw new Error('Chỉ nội dung đã được Reviewer phê duyệt mới được thay đổi trạng thái hiển thị.')
  }

  item.visibility = visibility
  return item
}

export function getAdminDashboardStats() {
  const visibilityItems = getAdminVisibilityItems()
  const reviewItems = getAdminReviewRequests()
  return {
    users: state.users.length,
    reviewers: state.reviewers.length,
    providers: state.providers.length,
    approvedCourses: state.courses.filter((course) => course.reviewStatus === REVIEW_STATUS.approved).length,
    lessons: state.lessons.filter((lesson) => lesson.reviewStatus === REVIEW_STATUS.approved).length,
    materials: state.materials.filter((material) => material.reviewStatus === REVIEW_STATUS.approved).length,
    enrollments: state.courses.reduce((total, course) => total + course.enrollments, 0),
    visible: visibilityItems.filter((item) => item.visibility === 'visible').length,
    hidden: visibilityItems.filter((item) => item.visibility === 'hidden').length,
    reviewQueue: reviewItems.length,
    unassigned: reviewItems.filter((item) => !item.assignedReviewerId).length,
  }
}

export function getRecommendationMetrics() {
  return recommendationMetrics
}

export function getAdminAnalytics(period = '30d') {
  return analyticsByPeriod[period] || analyticsByPeriod['30d']
}

export function getAdminProfile() {
  return state.profile
}

export function saveAdminProfile(values) {
  if (!values.fullName?.trim() || !values.email?.trim()) {
    throw new Error('Vui lòng nhập họ tên và email.')
  }

  const email = values.email.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error('Vui lòng nhập email hợp lệ.')
  }

  Object.assign(state.profile, {
    fullName: values.fullName.trim(),
    email,
    phone: values.phone?.trim() || '',
  })

  const adminUser = state.users.find((user) => user.role === ADMIN_ROLES.admin)
  if (adminUser) {
    adminUser.fullName = state.profile.fullName
    adminUser.email = state.profile.email
    adminUser.phone = state.profile.phone
  }

  return state.profile
}
