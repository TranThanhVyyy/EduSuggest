import api from '@/service/api'

function mapCourse(course) {
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || 'Khóa học chưa có tiêu đề',
    description: course.moTa || '',
    categoryId: course.maDanhMuc,
    category: course.danhMuc?.tenDanhMuc || (course.maDanhMuc ? `Danh mục #${course.maDanhMuc}` : 'Chưa phân loại'),
    provider: course.maNhaCungCap ? `Nhà cung cấp #${course.maNhaCungCap}` : 'Chưa có thông tin',
    level: course.trinhDo || '',
    duration: course.thoiLuong == null ? 'Chưa có thông tin' : `${course.thoiLuong}`,
    price: course.gia == null ? null : Number(course.gia),
    reviewStatus: course.trangThaiDuyet,
    visibility: course.trangThaiHienThi,
    lessons: (course.baiHocs || []).map((lesson) => ({
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
    })),
  }
}

function mapRecommendedCourse(course) {
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || 'Khóa học chưa có tiêu đề',
    description: course.moTa || '',
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
    lessonId: String(material.maBaiHoc),
    courseId: String(material.maKhoaHoc),
    title: material.tieuDe || 'Tài liệu chưa có tiêu đề',
    description: material.moTa || '',
    type: material.loai || '',
    score: Number(material.score),
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

export async function fetchRecommendedMaterials(courseId, { lessonId, limit = 10 } = {}) {
  const params = { course_id: Number(courseId), limit }
  if (lessonId != null) params.lesson_id = Number(lessonId)
  const { data } = await api.get('/recommendations/materials', { params })
  return (data.items || []).map(mapRecommendedMaterial)
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
