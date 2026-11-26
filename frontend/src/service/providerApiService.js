import api, { resolveMediaUrl } from '@/service/api'

export const PROVIDER_STATUS = Object.freeze({
  draft: 'Draft',
  pending: 'ChoKiemDuyet',
  approved: 'DaPheDuyet',
  rejected: 'TuChoi',
  changesRequested: 'YeuCauChinhSua',
})

export const PROVIDER_STATUS_LABELS = Object.freeze({
  [PROVIDER_STATUS.draft]: 'Bản nháp',
  [PROVIDER_STATUS.pending]: 'Chờ kiểm duyệt',
  [PROVIDER_STATUS.approved]: 'Đã phê duyệt',
  [PROVIDER_STATUS.rejected]: 'Bị từ chối',
  [PROVIDER_STATUS.changesRequested]: 'Yêu cầu chỉnh sửa',
})

const statusToUi = Object.freeze({
  DRAFT: 'Draft',
  PENDING: 'ChoKiemDuyet',
  APPROVED: 'DaPheDuyet',
  REJECTED: 'TuChoi',
  NEEDS_REVISION: 'YeuCauChinhSua',
})

function optionalNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function mapProviderReview(review) {
  return {
    ...review,
    status: statusToUi[review.trangThai] || review.trangThai || '',
    action: statusToUi[review.trangThai] || review.trangThai || 'Nhận xét',
    feedback: review.ghiChu || review.noiDungDanhGia || '',
    createdAt: review.ngayTao || '',
  }
}

export function providerErrorMessage(error, fallback = 'Không thể hoàn tất yêu cầu.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ')
  return error?.message || fallback
}

export function mapProviderCourse(course) {
  const lessons = (course.baiHocs || []).map((lesson) => ({
    id: String(lesson.maBaiHoc),
    title: lesson.tieuDe || '',
    description: '',
    duration: lesson.thoiLuong == null ? '' : `${lesson.thoiLuong} phút`,
    durationMinutes: lesson.thoiLuong,
    content: lesson.noiDung || '',
    video: lesson.duongDanVideo ? { title: lesson.tieuDe || 'Video bài học', url: lesson.duongDanVideo } : null,
    thuTu: lesson.thuTu,
    materials: (lesson.taiLieus || []).map(mapProviderMaterial),
  })).sort((first, second) => (first.thuTu ?? Number.MAX_SAFE_INTEGER) - (second.thuTu ?? Number.MAX_SAFE_INTEGER))
  const reviewStatus = course.trangThaiDuyet
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || '',
    coverImageUrl: resolveMediaUrl(course.hinhAnh),
    rawCoverImageUrl: course.hinhAnh || '',
    categoryId: course.maDanhMuc == null ? '' : String(course.maDanhMuc),
    category: course.maDanhMuc == null ? '' : `Mã danh mục ${course.maDanhMuc}`,
    shortDescription: course.moTa || '',
    description: course.moTa || '',
    estimatedDuration: course.thoiLuong == null ? '' : `${course.thoiLuong} phút`,
    durationMinutes: course.thoiLuong,
    level: course.trinhDo || '',
    price: course.gia,
    status: statusToUi[reviewStatus] || 'Draft',
    trangThaiDuyet: reviewStatus,
    visibility: course.trangThaiHienThi,
    submittedAt: '',
    updatedAt: course.ngayCapNhat || course.ngayTao || '',
    createdAt: course.ngayTao || '',
    reviewerName: '',
    reviewFeedback: course.lyDoTuChoi || '',
    // The current schema has lessons but no chapter entity. Keep them in a single
    // display group; this group is never sent to or persisted by the backend.
    lessons,
    materials: lessons.flatMap((lesson) => lesson.materials),
  }
}

export function mapProviderMaterial(material) {
  return {
    id: String(material.maTaiLieu),
    courseId: material.maKhoaHoc != null ? String(material.maKhoaHoc) : null,
    lessonId: material.maBaiHoc != null ? String(material.maBaiHoc) : null,
    categoryId: material.maDanhMuc != null ? Number(material.maDanhMuc) : null,
    title: material.tieuDe || '',
    description: material.moTa || '',
    documentType: material.loai || 'DOCUMENT',
    fileUrl: material.duongDanTep || '',
    fileName: '',
    mimeType: '',
    sizeBytes: null,
    status: statusToUi[material.trangThaiDuyet] || material.trangThaiDuyet || 'Draft',
    reviewStatus: statusToUi[material.trangThaiDuyet] || material.trangThaiDuyet || 'Draft',
    visibility: material.trangThaiHienThi || 'HIDDEN',
    rejectionReason: material.lyDoTuChoi || null,
    reviewedBy: material.maNguoiDuyet || null,
    reviewedAt: material.ngayDuyet || null,
    createdAt: material.ngayTao || '',
    updatedAt: material.ngayCapNhat || '',
  }
}

export async function loadProviderProfile() {
  const { data } = await api.get('/provider/profile')
  return data
}

export async function updateProviderProfile(values) {
  const payload = {}
  if (Object.hasOwn(values, 'introduction')) payload.tieuSu = values.introduction || null
  if (Object.hasOwn(values, 'expertise')) payload.chuyenMon = values.expertise || null
  if (!Object.keys(payload).length) throw new Error('Không có trường hồ sơ nào được Backend hỗ trợ để lưu.')
  const { data } = await api.put('/provider/profile', payload)
  return data
}

export async function loadProviderCourses() {
  const { data } = await api.get('/provider/courses')
  return data.map(mapProviderCourse)
}

export async function loadProviderCategories() {
  const { data } = await api.get('/provider/categories')
  return data.map((category) => ({
    id: String(category.maDanhMuc),
    name: category.tenDanhMuc || `Danh mục ${category.maDanhMuc}`,
    description: category.moTa || '',
  }))
}

export async function loadProviderCourse(courseId) {
  const { data } = await api.get(`/provider/courses/${courseId}`)
  return mapProviderCourse(data)
}

export async function createProviderCourseRecord(values) {
  const { data } = await api.post('/provider/courses', {
    maDanhMuc: Number(values.categoryId || values.category),
    tieuDe: values.title,
    moTa: values.description || values.shortDescription || null,
    hinhAnh: values.coverImagePath || null,
    trinhDo: values.level || null,
    gia: optionalNumber(values.price),
    thoiLuong: optionalNumber(values.durationMinutes),
  })
  return mapProviderCourse(data)
}

export async function updateProviderCourseRecord(courseId, values) {
  const payload = {}
  if (Object.hasOwn(values, 'title')) payload.tieuDe = values.title
  if (Object.hasOwn(values, 'categoryId') || Object.hasOwn(values, 'category')) {
    payload.maDanhMuc = Number(values.categoryId || values.category)
  }
  if (Object.hasOwn(values, 'description') || Object.hasOwn(values, 'shortDescription')) {
    payload.moTa = values.description || values.shortDescription || null
  }
  if (Object.hasOwn(values, 'coverImagePath')) payload.hinhAnh = values.coverImagePath || null
  if (Object.hasOwn(values, 'level')) payload.trinhDo = values.level || null
  if (Object.hasOwn(values, 'price')) payload.gia = optionalNumber(values.price)
  if (Object.hasOwn(values, 'durationMinutes')) payload.thoiLuong = optionalNumber(values.durationMinutes)
  if (!Object.keys(payload).length) throw new Error('Không có trường khóa học nào được Backend hỗ trợ để lưu.')
  const { data } = await api.put(`/provider/courses/${courseId}`, payload)
  return mapProviderCourse(data)
}

export async function uploadProviderCourseCover(file, courseId = null) {
  const formData = new FormData()
  formData.append('file', file)
  if (courseId) {
    const { data } = await api.post(`/provider/courses/${encodeURIComponent(courseId)}/cover-image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return {
      url: resolveMediaUrl(data.hinhAnh),
      rawUrl: data.hinhAnh || '',
      course: mapProviderCourse(data),
    }
  }
  const { data } = await api.post('/provider/media/course-cover', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return {
    url: resolveMediaUrl(data.url),
    rawUrl: data.url || '',
    course: null,
  }
}

export async function deleteProviderCourseRecord(courseId) {
  await api.delete(`/provider/courses/${courseId}`)
}

export async function submitProviderCourseRecord(courseId) {
  const { data } = await api.post(`/provider/courses/${courseId}/submit`)
  return mapProviderCourse(data)
}

export async function createProviderLesson(courseId, lesson, order) {
  const { data } = await api.post(`/provider/courses/${courseId}/lessons`, {
    tieuDe: lesson.title,
    noiDung: lesson.content || null,
    duongDanVideo: lesson.video?.url || null,
    thoiLuong: optionalNumber(lesson.durationMinutes),
    thuTu: order,
  })
  return data
}

export async function updateProviderLesson(courseId, lessonId, lesson) {
  const payload = {
    tieuDe: lesson.title,
    noiDung: lesson.content || null,
    duongDanVideo: lesson.video?.url || null,
    thoiLuong: optionalNumber(lesson.durationMinutes),
    thuTu: lesson.thuTu,
  }
  const { data } = await api.put(`/provider/courses/${courseId}/lessons/${lessonId}`, payload)
  return data
}

export async function deleteProviderLesson(courseId, lessonId) {
  await api.delete(`/provider/courses/${courseId}/lessons/${lessonId}`)
}

export async function createProviderMaterial(courseId, lessonId, values) {
  const payload = {
    tieuDe: values.title,
    loai: values.documentType || null,
    moTa: values.description || null,
  }
  if (values.fileUrl?.trim()) payload.duongDanTep = values.fileUrl.trim()
  const { data } = await api.post(`/provider/courses/${courseId}/lessons/${lessonId}/materials`, payload)
  return mapProviderMaterial(data)
}

export async function updateProviderMaterial(courseId, lessonId, materialId, values) {
  const payload = {
    tieuDe: values.title,
    loai: values.documentType || null,
    moTa: values.description || null,
  }
  if (values.fileUrl !== undefined) payload.duongDanTep = values.fileUrl
  const { data } = await api.put(`/provider/courses/${courseId}/lessons/${lessonId}/materials/${materialId}`, payload)
  return mapProviderMaterial(data)
}

export async function deleteProviderMaterial(courseId, lessonId, materialId) {
  await api.delete(`/provider/courses/${courseId}/lessons/${lessonId}/materials/${materialId}`)
}

export async function loadProviderReviews(courseId) {
  const { data } = await api.get(`/provider/courses/${courseId}/reviews`)
  return data
}

export async function loadProviderMaterials() {
  const { data } = await api.get('/provider/materials')
  return data.map(mapProviderMaterial)
}

export async function loadProviderMaterial(materialId) {
  const { data } = await api.get(`/provider/materials/${materialId}`)
  return mapProviderMaterial(data)
}

export async function createStandaloneMaterial(values) {
  const payload = {
    tieuDe: values.title,
    loai: values.documentType || null,
    moTa: values.description || null,
    maDanhMuc: values.categoryId ? Number(values.categoryId) : null,
    maKhoaHoc: values.courseId ? Number(values.courseId) : null,
    maBaiHoc: values.lessonId ? Number(values.lessonId) : null,
  }
  if (values.fileUrl?.trim()) payload.duongDanTep = values.fileUrl.trim()
  const { data } = await api.post('/provider/materials', payload)
  return mapProviderMaterial(data)
}

export async function uploadStandaloneMaterialFile(materialId, file) {
  const payload = new FormData()
  payload.append('file', file)
  const { data } = await api.post(`/provider/materials/${materialId}/file`, payload)
  return mapProviderMaterial(data)
}

export async function updateStandaloneMaterial(materialId, values) {
  const payload = {}
  if (values.title !== undefined) payload.tieuDe = values.title
  if (values.fileUrl !== undefined) payload.duongDanTep = values.fileUrl
  if (values.documentType !== undefined) payload.loai = values.documentType
  if (values.description !== undefined) payload.moTa = values.description
  if (values.categoryId !== undefined) payload.maDanhMuc = values.categoryId ? Number(values.categoryId) : null
  if (values.courseId !== undefined) payload.maKhoaHoc = values.courseId ? Number(values.courseId) : null
  if (values.lessonId !== undefined) payload.maBaiHoc = values.lessonId ? Number(values.lessonId) : null

  const { data } = await api.put(`/provider/materials/${materialId}`, payload)
  return mapProviderMaterial(data)
}

export async function deleteStandaloneMaterial(materialId) {
  await api.delete(`/provider/materials/${materialId}`)
}

export async function submitStandaloneMaterial(materialId) {
  const { data } = await api.post(`/provider/materials/${materialId}/submit`)
  return mapProviderMaterial(data)
}
