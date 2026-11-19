import { reactive } from 'vue'
import {
  demoCourses,
  demoEnrollments,
  demoExperts,
  demoLearningActivities,
  demoMaterials,
  demoRecommendations,
  demoUserProfile,
} from '@/data/userData'

const clone = (value) => JSON.parse(JSON.stringify(value))
const state = reactive({
  profile: clone(demoUserProfile),
  courses: clone(demoCourses),
  materials: clone(demoMaterials),
  experts: clone(demoExperts),
  enrollments: clone(demoEnrollments),
  recommendations: clone(demoRecommendations),
  activities: clone(demoLearningActivities),
  providerApplication: {
    status: 'not_applied',
    submittedAt: '',
    organization: '',
    expertise: '',
    experience: '',
    introduction: '',
    reason: '',
    rejectionReason: '',
  },
  expertReviews: [],
})

const now = () => new Date().toISOString()

export function getUserDemoNotice() {
  return 'Bản demo User dùng dữ liệu mẫu trong bộ nhớ của trình duyệt. Chưa có xác thực, API Backend, thanh toán hoặc dữ liệu cá nhân thật; thao tác sẽ mất khi tải lại trang.'
}

export function getUserProfile() {
  return state.profile
}

export function getUserRoles() {
  return [...state.profile.roles]
}

export function hasProviderRole() {
  return state.profile.roles.includes('Provider')
}

export function saveUserProfile(values) {
  const fullName = String(values.fullName || '').trim()
  const phone = String(values.phone || '').trim()
  const bio = String(values.bio || '').trim()
  const avatarUrl = String(values.avatarUrl || '').trim()
  if (!fullName) throw new Error('Vui lòng nhập họ tên.')
  if (phone && !/^[+()\d\s.-]{7,20}$/.test(phone)) throw new Error('Số điện thoại không hợp lệ.')
  if (avatarUrl && !/^blob:/.test(avatarUrl) && !/^https?:\/\//i.test(avatarUrl)) {
    throw new Error('Ảnh đại diện phải là tệp được chọn trong phiên hoặc URL HTTP/HTTPS.')
  }
  if (state.profile.avatarUrl !== avatarUrl && state.profile.avatarUrl.startsWith('blob:')) {
    URL.revokeObjectURL(state.profile.avatarUrl)
  }
  Object.assign(state.profile, { fullName, phone, bio, avatarUrl })
  return state.profile
}

export function getPublicCourses() {
  return state.courses.filter((course) => course.isPublic && course.reviewStatus === 'DaPheDuyet')
}

export function getPublicCourse(courseId) {
  return getPublicCourses().find((course) => course.id === courseId) || null
}

export function getEnrollment(courseId) {
  return state.enrollments.find((enrollment) => enrollment.courseId === courseId) || null
}

export function isEnrolled(courseId) {
  return Boolean(getEnrollment(courseId))
}

export function getEnrolledCourses() {
  return state.enrollments
    .map((enrollment) => ({
      enrollment,
      course: getPublicCourse(enrollment.courseId),
    }))
    .filter((entry) => entry.course)
    .sort((first, second) =>
      new Date(second.enrollment.lastAccessedAt || second.enrollment.enrolledAt)
        - new Date(first.enrollment.lastAccessedAt || first.enrollment.enrolledAt),
    )
}

export function getCourseProgress(courseId) {
  const course = getPublicCourse(courseId)
  const enrollment = getEnrollment(courseId)
  if (!course || !enrollment) return null
  const lessonCount = course.chapters.reduce((sum, chapter) => sum + chapter.lessons.length, 0)
  const completedCount = enrollment.completedLessonIds.length
  return {
    totalLessons: lessonCount,
    completedLessons: completedCount,
    percentage: lessonCount ? Math.round((completedCount / lessonCount) * 100) : 0,
    status: enrollment.status,
  }
}

export function enrollInCourse(courseId) {
  const course = getPublicCourse(courseId)
  if (!course) throw new Error('Không tìm thấy khóa học công khai.')
  const existing = getEnrollment(courseId)
  if (existing) return { status: 'already_enrolled', enrollment: existing }
  if (course.price > 0) return { status: 'payment_required', enrollment: null }

  const firstLessonId = course.chapters[0]?.lessons[0]?.id || ''
  const enrollment = {
    id: `ENROLL-DEMO-${Date.now()}`,
    courseId,
    status: 'in_progress',
    enrolledAt: now(),
    lastAccessedAt: now(),
    currentLessonId: firstLessonId,
    completedLessonIds: [],
  }
  state.enrollments.unshift(enrollment)
  state.activities.unshift({
    id: `ACT-${Date.now()}`,
    type: 'enrollment',
    title: `Đăng ký khóa học: ${course.title}`,
    createdAt: enrollment.enrolledAt,
    courseId,
  })
  return { status: 'enrolled', enrollment }
}

function findLesson(course, lessonId) {
  for (const chapter of course.chapters) {
    const lesson = chapter.lessons.find((item) => item.id === lessonId)
    if (lesson) return { chapter, lesson }
  }
  return null
}

export function getLearningCourse(courseId) {
  const course = getPublicCourse(courseId)
  const enrollment = getEnrollment(courseId)
  if (!course || !enrollment) return null
  return { course, enrollment }
}

export function setCurrentLesson(courseId, lessonId) {
  const access = getLearningCourse(courseId)
  if (!access) throw new Error('Bạn chưa có quyền truy cập khóa học này.')
  if (!findLesson(access.course, lessonId)) throw new Error('Không tìm thấy bài học trong khóa học.')
  access.enrollment.currentLessonId = lessonId
  access.enrollment.lastAccessedAt = now()
  return access.enrollment
}

export function markLessonCompleted(courseId, lessonId) {
  const access = getLearningCourse(courseId)
  if (!access) throw new Error('Bạn chưa có quyền truy cập khóa học này.')
  const lessonMatch = findLesson(access.course, lessonId)
  if (!lessonMatch) throw new Error('Không tìm thấy bài học trong khóa học.')
  if (!access.enrollment.completedLessonIds.includes(lessonId)) {
    access.enrollment.completedLessonIds.push(lessonId)
    state.activities.unshift({
      id: `ACT-${Date.now()}`,
      type: 'lesson',
      title: `Hoàn thành: ${lessonMatch.lesson.title}`,
      createdAt: now(),
      courseId,
    })
  }
  const progress = getCourseProgress(courseId)
  access.enrollment.status = progress.percentage === 100 ? 'completed' : 'in_progress'
  if (access.enrollment.status === 'completed') access.enrollment.completedAt ||= now()
  access.enrollment.lastAccessedAt = now()
  return progress
}

export function getLearningStats() {
  const enrollments = getEnrolledCourses()
  const progress = enrollments.map(({ course }) => getCourseProgress(course.id))
  return {
    totalCourses: enrollments.length,
    inProgressCourses: enrollments.filter(({ enrollment }) => enrollment.status === 'in_progress').length,
    completedCourses: enrollments.filter(({ enrollment }) => enrollment.status === 'completed').length,
    completedLessons: progress.reduce((sum, item) => sum + item.completedLessons, 0),
  }
}

export function getLearningHistory() {
  return getEnrolledCourses().map(({ course, enrollment }) => ({
    course,
    enrollment,
    progress: getCourseProgress(course.id),
  }))
}

export function getRecentLearningActivities(limit = 6) {
  return state.activities.slice(0, limit)
}

export function getPublicMaterials() {
  return state.materials.filter((material) => material.isAccessible
    && isEnrolled(material.courseId)
    && getPublicCourse(material.courseId))
}

export function getPublicMaterial(materialId) {
  return getPublicMaterials().find((material) => material.id === materialId) || null
}

export function getRecommendedCourses() {
  return state.recommendations.courses
    .map((courseId) => getPublicCourse(courseId))
    .filter(Boolean)
}

export function getRecommendedMaterials() {
  return state.recommendations.materials
    .map((materialId) => getPublicMaterial(materialId))
    .filter(Boolean)
}

export function getExperts() {
  return state.experts
}

export function getExpertReviewHistory() {
  return state.expertReviews
}

export function submitExpertReview(expertId, values) {
  const expert = state.experts.find((record) => record.id === expertId)
  if (!expert) throw new Error('Không tìm thấy chuyên gia.')
  if (!expert.canReview) {
    throw new Error(expert.eligibilityMessage || 'Điều kiện đánh giá chưa được xác nhận bởi Backend.')
  }
  const rating = Number(values.rating)
  const comment = String(values.comment || '').trim()
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) throw new Error('Chọn số sao từ 1 đến 5.')
  if (!comment) throw new Error('Nhập nội dung nhận xét.')
  if (state.expertReviews.some((review) => review.expertId === expertId)) {
    throw new Error('Bạn đã gửi đánh giá cho chuyên gia này.')
  }
  const review = { id: `REVIEW-${Date.now()}`, expertId, rating, comment, createdAt: now() }
  state.expertReviews.unshift(review)
  return review
}

export function getProviderApplication() {
  return state.providerApplication
}

export function submitProviderApplication(values) {
  const required = ['phone', 'expertise', 'reason']
  if (required.some((key) => !String(values[key] || '').trim())) {
    throw new Error('Vui lòng nhập số điện thoại, lĩnh vực chuyên môn và lý do đăng ký.')
  }
  if (['pending', 'approved'].includes(state.providerApplication.status)) {
    throw new Error('Hồ sơ đang chờ hoặc đã được xét duyệt, không thể gửi thêm.')
  }
  if (hasProviderRole()) throw new Error('Tài khoản đã có vai trò Provider.')

  Object.assign(state.providerApplication, {
    status: 'pending',
    submittedAt: now(),
    organization: String(values.organization || '').trim(),
    expertise: String(values.expertise || '').trim(),
    experience: String(values.experience || '').trim(),
    introduction: String(values.introduction || '').trim(),
    reason: String(values.reason || '').trim(),
    rejectionReason: '',
  })
  return state.providerApplication
}
