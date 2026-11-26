import api, { resolveMediaUrl } from '@/service/api'

function mapCourse(course) {
  const publicSyllabus = (course.deCuongCongKhai || []).map((lesson) => ({
    id: String(lesson.maBaiHoc),
    title: lesson.tieuDe || 'Bài học chưa có tiêu đề',
    order: lesson.thuTu,
    duration: lesson.thoiLuong,
  }))
  const lessons = (course.baiHocs || []).map((lesson) => ({
    id: String(lesson.maBaiHoc),
    title: lesson.tieuDe || 'Bài học chưa có tiêu đề',
    content: lesson.noiDung || '',
    duration: lesson.thoiLuong,
    materials: (lesson.taiLieus || []).map((material) => ({
      id: String(material.maTaiLieu),
      title: material.tieuDe || 'Tài liệu',
      url: material.duongDanTep || '',
      type: material.loai || '',
    })),
  }))
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || 'Khóa học chưa có tiêu đề',
    description: course.moTa || '',
    coverImageUrl: resolveMediaUrl(course.hinhAnh),
    categoryId: course.maDanhMuc,
    category: course.danhMuc?.tenDanhMuc || (course.maDanhMuc ? `Danh mục #${course.maDanhMuc}` : 'Chưa phân loại'),
    provider: course.tenNhaCungCap || (course.maNhaCungCap ? `Nhà cung cấp #${course.maNhaCungCap}` : 'Chưa có thông tin'),
    level: course.trinhDo || '',
    duration: course.thoiLuong == null ? 'Chưa có thông tin' : `${course.thoiLuong}`,
    price: course.gia == null ? null : Number(course.gia),
    reviewStatus: course.trangThaiDuyet,
    visibility: course.trangThaiHienThi,
    lessonCount: course.soLuongBaiHoc != null ? Number(course.soLuongBaiHoc) : Math.max(lessons.length, publicSyllabus.length),
    publicSyllabus,
    lessons,
  }
}

function mapRecommendedCourse(course) {
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || 'Khóa học chưa có tiêu đề',
    description: course.moTa || '',
    coverImageUrl: resolveMediaUrl(course.hinhAnh),
    categoryId: course.maDanhMuc,
    category: '',
    level: course.trinhDo || '',
    duration: course.thoiLuong == null ? '' : `${course.thoiLuong}`,
    price: course.gia == null ? null : Number(course.gia),
    score: course.score,
    reasonCodes: course.reasonCodes || [],
  }
}

function mapRecommendedMaterial(material) {
  return {
    id: String(material.maTaiLieu),
    lessonId: material.maBaiHoc != null ? String(material.maBaiHoc) : null,
    courseId: material.maKhoaHoc != null ? String(material.maKhoaHoc) : null,
    title: material.tieuDe || 'Tài liệu chưa có tiêu đề',
    description: material.moTa || '',
    type: material.loai || '',
    score: material.score != null ? Number(material.score) : undefined,
    reasonCodes: material.reasonCodes || [],
  }
}

export async function fetchUserCourses({ query, categoryId } = {}) {
  const params = { limit: 100 }
  if (query?.trim()) params.query = query.trim()
  if (categoryId) params.category_id = Number(categoryId)
  const { data } = await api.get('/courses', { params })
  return data.map(mapCourse)
}

export async function fetchUserCategories() {
  const { data } = await api.get('/categories')
  return data.map((category) => ({ id: String(category.maDanhMuc), name: category.tenDanhMuc || 'Danh mục chưa có tên' }))
}

export async function fetchUserCourse(courseId) {
  const { data } = await api.get(`/courses/${encodeURIComponent(courseId)}`)
  return mapCourse(data)
}

export async function fetchRecommendedCourses({ limit = 10 } = {}) {
  const { data } = await api.get('/recommendations/courses', { params: { limit } })
  return {
    items: (data.items || []).map(mapRecommendedCourse),
    strategy: data.strategy,
    personalized: Boolean(data.personalized),
  }
}

export async function fetchSimilarCourses(courseId, { limit = 6 } = {}) {
  const { data } = await api.get(`/courses/${encodeURIComponent(courseId)}/similar`, { params: { limit } })
  return data.map(mapRecommendedCourse)
}

export async function fetchRecommendedMaterials(courseId = null, { lessonId, limit = 10 } = {}) {
  const result = await fetchRecommendedMaterialsWithMeta(courseId, { lessonId, limit })
  return result.items
}

export async function fetchRecommendedMaterialsWithMeta(courseId = null, { lessonId, limit = 10 } = {}) {
  if (courseId == null) {
    const enrollments = await fetchMyEnrollments()
    const courses = [...new Map(
      enrollments
        .filter((item) => item.course?.id)
        .map((item) => [String(item.course.id), item.course]),
    ).values()]

    if (!courses.length) {
      return { items: [], strategy: 'none', personalized: false, hasEnrollments: false, failedCourseCount: 0 }
    }

    const results = await Promise.allSettled(
      courses.map(async (course) => ({
        course,
        items: await requestRecommendedMaterials(course.id, { limit }),
      }))
    )
    const successful = results.filter((result) => result.status === 'fulfilled')
    const failures = results.filter((result) => result.status === 'rejected')
    if (!successful.length && failures.length) throw failures[0].reason

    const items = successful.flatMap(({ value }) => value.items.map((item) => ({
      ...item,
      courseTitle: value.course.title,
      lessonTitle: item.lessonId ? `Bài học #${item.lessonId}` : '',
    })))
    return {
      items: [...new Map(items.map((item) => [item.id, item])).values()],
      strategy: items.length ? 'content_based' : 'none',
      personalized: true,
      hasEnrollments: true,
      failedCourseCount: failures.length,
    }
  }

  const items = await requestRecommendedMaterials(courseId, { lessonId, limit })
  return { items, strategy: items.length ? 'content_based' : 'none', personalized: true, hasEnrollments: true, failedCourseCount: 0 }
}

async function requestRecommendedMaterials(courseId, { lessonId, limit = 10 } = {}) {
  const params = { limit }
  params.course_id = Number(courseId)
  if (lessonId != null && Number(lessonId) > 0) {
    params.lesson_id = Number(lessonId)
  }
  const { data } = await api.get('/recommendations/materials', { params })
  return (data.items || []).map(mapRecommendedMaterial)
}

export async function fetchPublicMaterials({ query, categoryId, materialType, page = 1, pageSize = 20 } = {}) {
  const params = { page, page_size: pageSize }
  if (query?.trim()) params.query = query.trim()
  if (categoryId) params.category_id = Number(categoryId)
  if (materialType?.trim()) params.material_type = materialType.trim()
  const { data } = await api.get('/materials', { params })
  if (Array.isArray(data)) {
    return {
      items: data.map(mapRecommendedMaterial),
      total: data.length,
      page,
      pageSize,
      totalPages: data.length ? 1 : 0,
    }
  }
  return {
    items: (data.items || []).map(mapRecommendedMaterial),
    total: Number(data.total ?? 0),
    page: Number(data.page ?? page),
    pageSize: Number(data.page_size ?? pageSize),
    totalPages: Number(data.total_pages ?? 0),
  }
}

export async function fetchPublicMaterial(materialId) {
  const { data } = await api.get(`/materials/${encodeURIComponent(materialId)}`)
  return mapRecommendedMaterial(data)
}

export async function fetchSimilarMaterials(materialId, { limit = 6 } = {}) {
  const { data } = await api.get(`/materials/${encodeURIComponent(materialId)}/similar`, { params: { limit } })
  return data.map(mapRecommendedMaterial)
}

export async function enrollUserInCourse(courseId) {
  const { data } = await api.post(`/courses/${encodeURIComponent(courseId)}/enrollments`)
  return mapEnrollment(data)
}

export async function fetchMyEnrollments() {
  const { data } = await api.get('/enrollments')
  return data.map(mapEnrollment)
}

export async function fetchLearningCourse(courseId) {
  const { data } = await api.get(`/learning/courses/${encodeURIComponent(courseId)}`)
  return {
    course: mapCourse(data.khoaHoc),
    lessons: (data.baiHocs || []).map((lesson) => ({
      id: String(lesson.maBaiHoc),
      title: lesson.tieuDe || 'Bài học chưa có tiêu đề',
      content: lesson.noiDung || '',
      videoUrl: lesson.duongDanVideo || '',
      completed: Boolean(lesson.daHoanThanh),
      materials: (lesson.taiLieus || []).map((material) => ({
        id: String(material.maTaiLieu), title: material.tieuDe || 'Tài liệu',
        url: material.duongDanTep || '', type: material.loai || '',
      })),
    })),
  }
}

export async function fetchLearningProgress(courseId) {
  const { data } = await api.get(`/learning/courses/${encodeURIComponent(courseId)}/progress`)
  return {
    courseId: String(data.maKhoaHoc), totalLessons: data.tongBaiHoc,
    completedLessons: data.baiHocHoanThanh, percentage: Number(data.tienDo),
    lastActivityAt: data.ngayHoatDongGanNhat,
  }
}

export async function completeLearningLesson(courseId, lessonId) {
  const { data } = await api.post(`/learning/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/complete`)
  return {
    courseId: String(data.maKhoaHoc), totalLessons: data.tongBaiHoc,
    completedLessons: data.baiHocHoanThanh, percentage: Number(data.tienDo),
    lastActivityAt: data.ngayHoatDongGanNhat,
  }
}

export async function fetchLearningHistory() {
  const { data } = await api.get('/learning/history')
  return data.map((item) => ({
    id: String(item.maLichSu), course: mapCourse(item.khoaHoc),
    lesson: { id: String(item.maBaiHoc), title: item.baiHoc?.tieuDe || 'Bài học' },
    status: item.tienDo, duration: item.thoiGianXem, createdAt: item.ngayTao,
  }))
}

function mapEnrollment(item) {
  return {
    id: String(item.maDangKy), course: mapCourse(item.khoaHoc),
    enrolledAt: item.ngayDangKy, progress: Number(item.tienDo || 0),
    completedAt: item.ngayHoanThanh, totalLessons: item.tongBaiHoc || 0,
    completedLessons: item.baiHocHoanThanh || 0,
    status: item.ngayHoanThanh ? 'completed' : 'in_progress',
  }
}
