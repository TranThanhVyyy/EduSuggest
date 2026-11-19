import { reactive } from 'vue'
import {
  PROVIDER_ID,
  providerCategories,
  providerCourses,
  providerProfile,
} from '@/data/providerData'

export const PROVIDER_STATUS = Object.freeze({
  draft: 'Draft',
  pendingAssignment: 'PendingAssignment',
  pending: 'ChoKiemDuyet',
  reviewing: 'DangKiemDuyet',
  approved: 'DaPheDuyet',
  rejected: 'TuChoi',
  changesRequested: 'YeuCauChinhSua',
})

export const PROVIDER_STATUS_LABELS = Object.freeze({
  [PROVIDER_STATUS.draft]: 'Bản nháp',
  [PROVIDER_STATUS.pendingAssignment]: 'Chờ phân công',
  [PROVIDER_STATUS.pending]: 'Chờ kiểm duyệt',
  [PROVIDER_STATUS.reviewing]: 'Đang kiểm duyệt',
  [PROVIDER_STATUS.approved]: 'Đã phê duyệt',
  [PROVIDER_STATUS.rejected]: 'Bị từ chối',
  [PROVIDER_STATUS.changesRequested]: 'Yêu cầu chỉnh sửa',
})

const editableStatuses = new Set([
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
])

const editableCourseFields = new Set([
  'title',
  'category',
  'coverImageUrl',
  'coverImageName',
  'shortDescription',
  'description',
  'objectives',
  'audience',
  'prerequisites',
  'outcomes',
  'estimatedDuration',
  'chapters',
  'materials',
])

const copy = (value) => JSON.parse(JSON.stringify(value))
const state = reactive({
  profile: copy(providerProfile),
  courses: copy(providerCourses),
  activities: [],
})

function createId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function now() {
  return new Date().toISOString()
}

function assertOwnedCourse(courseId) {
  const course = state.courses.find(
    (record) => record.id === courseId && record.ownerId === PROVIDER_ID,
  )
  if (!course) throw new Error('Không tìm thấy khóa học trong dữ liệu Provider hiện tại.')
  return course
}

function assertEditableCourse(course) {
  if (!editableStatuses.has(course.status)) {
    throw new Error('Khóa học đang chờ hoặc đã hoàn tất kiểm duyệt nên không thể chỉnh sửa ở trạng thái này.')
  }
}

function addActivity(action, course, detail = '') {
  state.activities.unshift({
    id: createId('ACT'),
    action,
    title: course.title || 'Khóa học mới',
    detail,
    createdAt: now(),
  })
}

function touchCourse(course, action, detail = '') {
  course.updatedAt = now()
  addActivity(action, course, detail)
}

function normalizeMediaUrl(value, label) {
  const url = String(value || '').trim()
  if (!url) return ''

  let parsed
  try {
    parsed = new URL(url)
  } catch {
    throw new Error(`Đường dẫn ${label} không hợp lệ.`)
  }

  if (!['http:', 'https:', 'blob:'].includes(parsed.protocol)) {
    throw new Error(`Đường dẫn ${label} phải dùng HTTP, HTTPS hoặc tệp đã chọn trong phiên.`)
  }
  return url
}

function revokeObjectUrl(value) {
  if (typeof value === 'string' && value.startsWith('blob:')) URL.revokeObjectURL(value)
}

function getCourseObjectUrls(course) {
  const urls = new Set()
  if (course.coverImageUrl?.startsWith('blob:')) urls.add(course.coverImageUrl)
  for (const chapter of course.chapters || []) {
    for (const lesson of chapter.lessons || []) {
      if (lesson.video?.url?.startsWith('blob:')) urls.add(lesson.video.url)
      if (lesson.video?.thumbnailUrl?.startsWith('blob:')) urls.add(lesson.video.thumbnailUrl)
    }
  }
  for (const material of course.materials || []) {
    if (material.fileUrl?.startsWith('blob:')) urls.add(material.fileUrl)
  }
  return urls
}

export function getProviderCategories() {
  return [...providerCategories]
}

export function getProviderProfile() {
  return state.profile
}

export function saveProviderProfile(values) {
  const fullName = String(values.fullName || '').trim()
  const email = String(values.email || '').trim()
  if (!fullName || !email) throw new Error('Vui lòng nhập họ tên và email.')
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Vui lòng nhập email hợp lệ.')
  if (email.toLocaleLowerCase('vi') !== state.profile.email.toLocaleLowerCase('vi')) {
    throw new Error('Không thể thay đổi email khi chưa có bước xác minh từ Backend.')
  }
  const avatarUrl = String(values.avatarUrl || '').trim()
  if (state.profile.avatarUrl !== avatarUrl) revokeObjectUrl(state.profile.avatarUrl)

  Object.assign(state.profile, {
    fullName,
    email,
    phone: String(values.phone || '').trim(),
    organization: String(values.organization || '').trim(),
    introduction: String(values.introduction || '').trim(),
    expertise: String(values.expertise || '').trim(),
    experience: String(values.experience || '').trim(),
    avatarUrl,
  })
  return state.profile
}

export function getProviderCourses() {
  return state.courses
    .filter((course) => course.ownerId === PROVIDER_ID)
    .sort((first, second) => new Date(second.updatedAt) - new Date(first.updatedAt))
}

export function getProviderCourse(courseId) {
  return assertOwnedCourse(courseId)
}

export function createProviderCourse() {
  const timestamp = now()
  const course = {
    id: createId('COURSE'),
    ownerId: PROVIDER_ID,
    title: '',
    category: '',
    coverImageUrl: '',
    coverImageName: '',
    shortDescription: '',
    description: '',
    objectives: '',
    audience: '',
    prerequisites: '',
    outcomes: '',
    estimatedDuration: '',
    chapters: [],
    materials: [],
    status: PROVIDER_STATUS.draft,
    reviewerName: '',
    submittedAt: '',
    createdAt: timestamp,
    updatedAt: timestamp,
    visibility: null,
    reviewHistory: [],
  }
  state.courses.unshift(course)
  addActivity('Tạo bản nháp', course)
  return course
}

export function saveProviderCourse(courseId, values) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const previousObjectUrls = getCourseObjectUrls(course)
  const normalized = {}

  for (const [key, value] of Object.entries(values)) {
    if (editableCourseFields.has(key)) normalized[key] = copy(value)
  }

  Object.assign(course, normalized)
  const nextObjectUrls = getCourseObjectUrls(course)
  for (const url of previousObjectUrls) {
    if (!nextObjectUrls.has(url)) revokeObjectUrl(url)
  }
  touchCourse(course, 'Cập nhật khóa học')
  return course
}

export function deleteProviderCourse(courseId) {
  const course = assertOwnedCourse(courseId)
  if (course.status !== PROVIDER_STATUS.draft) {
    throw new Error('Chỉ có thể xóa khóa học chưa gửi kiểm duyệt.')
  }
  revokeObjectUrl(course.coverImageUrl)
  for (const material of course.materials) revokeObjectUrl(material.fileUrl)
  for (const chapter of course.chapters) {
    for (const lesson of chapter.lessons) {
      revokeObjectUrl(lesson.video?.url)
      revokeObjectUrl(lesson.video?.thumbnailUrl)
    }
  }
  state.courses = state.courses.filter((record) => record.id !== courseId)
}

export function addProviderChapter(courseId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = {
    id: createId('CH'),
    title: `Chương ${course.chapters.length + 1}`,
    description: '',
    lessons: [],
  }
  course.chapters.push(chapter)
  touchCourse(course, 'Thêm chương')
  return chapter
}

export function saveProviderChapter(courseId, chapterId, values) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = course.chapters.find((record) => record.id === chapterId)
  if (!chapter) throw new Error('Không tìm thấy chương.')
  chapter.title = String(values.title || '').trim()
  chapter.description = String(values.description || '').trim()
  touchCourse(course, 'Cập nhật chương', chapter.title)
  return chapter
}

export function deleteProviderChapter(courseId, chapterId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = course.chapters.find((record) => record.id === chapterId)
  if (!chapter) throw new Error('Không tìm thấy chương.')
  for (const lesson of chapter.lessons) revokeObjectUrl(lesson.video?.url)
  const lessonIds = new Set(chapter.lessons.map((lesson) => lesson.id))
  course.chapters = course.chapters.filter((record) => record.id !== chapterId)
  course.materials.forEach((material) => {
    if (lessonIds.has(material.lessonId)) material.lessonId = ''
  })
  touchCourse(course, 'Xóa chương', chapter.title)
}

export function moveProviderChapter(courseId, chapterId, direction) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const index = course.chapters.findIndex((chapter) => chapter.id === chapterId)
  const nextIndex = index + direction
  if (index < 0 || nextIndex < 0 || nextIndex >= course.chapters.length) return
  ;[course.chapters[index], course.chapters[nextIndex]] = [course.chapters[nextIndex], course.chapters[index]]
  touchCourse(course, 'Sắp xếp chương')
}

export function addProviderLesson(courseId, chapterId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = course.chapters.find((record) => record.id === chapterId)
  if (!chapter) throw new Error('Không tìm thấy chương.')
  const lesson = {
    id: createId('LESSON'),
    title: '',
    description: '',
    duration: '',
    content: '',
    video: null,
  }
  chapter.lessons.push(lesson)
  touchCourse(course, 'Thêm bài học', chapter.title)
  return lesson
}

export function saveProviderLesson(courseId, chapterId, lessonId, values) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const lesson = course.chapters
    .find((chapter) => chapter.id === chapterId)
    ?.lessons.find((record) => record.id === lessonId)
  if (!lesson) throw new Error('Không tìm thấy bài học.')
  Object.assign(lesson, {
    title: String(values.title || '').trim(),
    description: String(values.description || '').trim(),
    duration: String(values.duration || '').trim(),
    content: String(values.content || '').trim(),
  })
  touchCourse(course, 'Cập nhật bài học', lesson.title)
  return lesson
}

export function deleteProviderLesson(courseId, chapterId, lessonId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = course.chapters.find((record) => record.id === chapterId)
  if (!chapter) throw new Error('Không tìm thấy chương.')
  const lesson = chapter.lessons.find((record) => record.id === lessonId)
  if (!lesson) throw new Error('Không tìm thấy bài học.')
  revokeObjectUrl(lesson.video?.url)
  chapter.lessons = chapter.lessons.filter((record) => record.id !== lessonId)
  course.materials.forEach((material) => {
    if (material.lessonId === lessonId) material.lessonId = ''
  })
  touchCourse(course, 'Xóa bài học', lesson.title)
}

export function moveProviderLesson(courseId, chapterId, lessonId, direction) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const chapter = course.chapters.find((record) => record.id === chapterId)
  if (!chapter) throw new Error('Không tìm thấy chương.')
  const index = chapter.lessons.findIndex((lesson) => lesson.id === lessonId)
  const nextIndex = index + direction
  if (index < 0 || nextIndex < 0 || nextIndex >= chapter.lessons.length) return
  ;[chapter.lessons[index], chapter.lessons[nextIndex]] = [chapter.lessons[nextIndex], chapter.lessons[index]]
  touchCourse(course, 'Sắp xếp bài học', chapter.title)
}

export function saveProviderVideo(courseId, chapterId, lessonId, values) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const lesson = course.chapters
    .find((chapter) => chapter.id === chapterId)
    ?.lessons.find((record) => record.id === lessonId)
  if (!lesson) throw new Error('Không tìm thấy bài học.')
  const url = normalizeMediaUrl(values.url, 'video')
  const thumbnailUrl = normalizeMediaUrl(values.thumbnailUrl, 'ảnh thumbnail')
  const title = String(values.title || '').trim()
  const description = String(values.description || '').trim()
  if ((title || description || values.duration || thumbnailUrl) && !url) {
    throw new Error('Chọn tệp video thực tế hoặc nhập URL video hợp lệ.')
  }
  if (url && !title) throw new Error('Vui lòng nhập tên video.')
  if (lesson.video?.url !== url) revokeObjectUrl(lesson.video?.url)
  if (lesson.video?.thumbnailUrl !== thumbnailUrl) revokeObjectUrl(lesson.video?.thumbnailUrl)
  lesson.video = url || title || description || values.duration || thumbnailUrl
    ? {
        title,
        url,
        duration: String(values.duration || '').trim(),
        description,
        thumbnailUrl,
        localFileName: String(values.localFileName || '').trim(),
      }
    : null
  touchCourse(course, url ? 'Cập nhật video' : 'Xóa video', lesson.title)
  return lesson.video
}

export function saveProviderMaterial(courseId, values) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const title = String(values.title || '').trim()
  if (!title) throw new Error('Vui lòng nhập tên tài liệu.')
  const fileUrl = normalizeMediaUrl(values.fileUrl, 'tài liệu')
  const lessonId = String(values.lessonId || '')
  if (lessonId && !course.chapters.some((chapter) => chapter.lessons.some((lesson) => lesson.id === lessonId))) {
    throw new Error('Bài học liên quan không thuộc khóa học này.')
  }

  const existing = values.id
    ? course.materials.find((material) => material.id === values.id)
    : null
  if (values.id && !existing) throw new Error('Không tìm thấy tài liệu.')
  if (existing && existing.fileUrl !== fileUrl) revokeObjectUrl(existing.fileUrl)
  const material = {
    id: existing?.id || createId('MAT'),
    title,
    description: String(values.description || '').trim(),
    documentType: String(values.documentType || '').trim(),
    fileName: String(values.fileName || '').trim(),
    mimeType: String(values.mimeType || '').trim(),
    sizeBytes: Number(values.sizeBytes) || null,
    fileUrl,
    lessonId,
    createdAt: existing?.createdAt || now(),
  }

  if (existing) Object.assign(existing, material)
  else course.materials.push(material)
  touchCourse(course, existing ? 'Cập nhật tài liệu' : 'Thêm tài liệu', title)
  return material
}

export function deleteProviderMaterial(courseId, materialId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const material = course.materials.find((record) => record.id === materialId)
  if (!material) throw new Error('Không tìm thấy tài liệu.')
  revokeObjectUrl(material.fileUrl)
  course.materials = course.materials.filter((record) => record.id !== materialId)
  touchCourse(course, 'Xóa tài liệu', material.title)
}

export function validateProviderCourse(course) {
  const issues = []
  if (!course.title.trim()) issues.push('Nhập tên khóa học.')
  if (!course.category) issues.push('Chọn danh mục.')
  if (!course.shortDescription.trim()) issues.push('Nhập mô tả ngắn.')
  if (!course.description.trim()) issues.push('Nhập mô tả chi tiết.')
  if (!course.coverImageUrl) issues.push('Thêm ảnh đại diện khóa học.')
  if (!course.objectives.trim()) issues.push('Nhập mục tiêu khóa học.')
  if (!course.audience.trim()) issues.push('Nhập đối tượng học viên.')
  if (!course.prerequisites.trim()) issues.push('Nhập kiến thức đầu vào hoặc ghi rõ không yêu cầu.')
  if (!course.outcomes.trim()) issues.push('Nhập kết quả học viên đạt được.')
  if (!course.estimatedDuration.trim()) issues.push('Nhập thời lượng dự kiến.')
  if (!course.chapters.length) issues.push('Thêm ít nhất một chương.')
  for (const [chapterIndex, chapter] of course.chapters.entries()) {
    if (!chapter.title.trim()) issues.push(`Nhập tên chương ${chapterIndex + 1}.`)
    if (!chapter.lessons.length) issues.push(`Thêm ít nhất một bài học cho chương ${chapterIndex + 1}.`)
    for (const [lessonIndex, lesson] of chapter.lessons.entries()) {
      if (!lesson.title.trim()) issues.push(`Nhập tên bài học ${lessonIndex + 1} của chương ${chapterIndex + 1}.`)
      if (!lesson.content.trim() && !lesson.video?.url) {
        issues.push(`Bổ sung nội dung văn bản hoặc video cho bài học "${lesson.title || lessonIndex + 1}".`)
      }
    }
  }
  return issues
}

export function submitProviderCourseForReview(courseId) {
  const course = assertOwnedCourse(courseId)
  assertEditableCourse(course)
  const issues = validateProviderCourse(course)
  if (issues.length) throw new Error(issues.join(' '))

  const resubmission = course.status === PROVIDER_STATUS.rejected
    || course.status === PROVIDER_STATUS.changesRequested
  course.status = PROVIDER_STATUS.pending
  course.submittedAt = now()
  course.reviewerName = ''
  course.reviewHistory ||= []
  course.reviewHistory.push({
    action: resubmission ? 'resubmitted' : 'submitted',
    createdAt: course.submittedAt,
  })
  touchCourse(course, resubmission ? 'Gửi lại kiểm duyệt' : 'Gửi kiểm duyệt')
  return course
}

export function getProviderCourseTimeline(courseId) {
  const course = assertOwnedCourse(courseId)
  const timeline = [{ action: 'Tạo khóa học', createdAt: course.createdAt }]
  for (const entry of course.reviewHistory || []) {
    timeline.push({
      action: entry.action === 'resubmitted' ? 'Gửi lại kiểm duyệt' : 'Gửi kiểm duyệt',
      createdAt: entry.createdAt,
    })
  }
  if (course.reviewerName) {
    timeline.push({
      action: 'Reviewer được phân công',
      detail: course.reviewerName,
      createdAt: course.assignedAt || '',
    })
  }
  if (course.reviewedAt) {
    timeline.push({
      action: PROVIDER_STATUS_LABELS[course.status] || course.status,
      detail: course.reviewFeedback || '',
      createdAt: course.reviewedAt,
    })
  }
  return timeline
}

export function getProviderReviewRequests() {
  return getProviderCourses().filter((course) => course.status !== PROVIDER_STATUS.draft)
}

export function getProviderReviewHistory() {
  return getProviderReviewRequests().flatMap((course) => {
    const history = [...(course.reviewHistory || [])]
    if (course.submittedAt && !history.some((entry) => entry.action === 'submitted' || entry.action === 'resubmitted')) {
      history.push({ action: 'submitted', createdAt: course.submittedAt })
    }
    return history.map((entry, index) => ({
      id: `${course.id}-${index}`,
      courseId: course.id,
      title: course.title,
      category: course.category,
      action: entry.action,
      createdAt: entry.createdAt,
      reviewerName: course.reviewerName || '',
      status: course.status,
      feedback: course.reviewFeedback || '',
    }))
  }).sort((first, second) => new Date(second.createdAt) - new Date(first.createdAt))
}

export function getProviderDashboardData() {
  const courses = getProviderCourses()
  const statusCounts = Object.fromEntries(
    Object.values(PROVIDER_STATUS).map((status) => [
      status,
      courses.filter((course) => course.status === status).length,
    ]),
  )
  return {
    total: courses.length,
    statusCounts,
    recentCourses: courses.slice(0, 5),
    activities: state.activities.slice(0, 6),
  }
}

export function getProviderNotifications() {
  return getProviderCourses()
    .filter((course) => course.reviewerName || course.status === PROVIDER_STATUS.approved
      || course.status === PROVIDER_STATUS.rejected
      || course.status === PROVIDER_STATUS.changesRequested)
    .map((course) => ({
      id: course.id,
      title: course.status === PROVIDER_STATUS.approved
        ? 'Khóa học đã được phê duyệt'
        : course.status === PROVIDER_STATUS.rejected
          ? 'Khóa học bị từ chối'
          : course.status === PROVIDER_STATUS.changesRequested
            ? 'Khóa học cần chỉnh sửa'
            : 'Reviewer đã được phân công',
      detail: course.title,
      updatedAt: course.updatedAt,
    }))
}

export function getProviderDemoNotice() {
  return 'Đây là giao diện minh họa dùng dữ liệu trong bộ nhớ của trình duyệt. Chưa có xác thực, phân quyền, lưu trữ tệp hoặc kết nối Backend.'
}
