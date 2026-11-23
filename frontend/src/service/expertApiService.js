import api from '@/service/api'

const statusMap = {
  PENDING: 'ChoKiemDuyet',
  APPROVED: 'DaPheDuyet',
  REJECTED: 'TuChoi',
  NEEDS_REVISION: 'YeuCauChinhSua',
}

function mapCourse(course) {
  return {
    id: String(course.maKhoaHoc),
    title: course.tieuDe || 'Khóa học chưa có tiêu đề',
    description: course.moTa || '',
    category: course.maDanhMuc ? `Danh mục #${course.maDanhMuc}` : '',
    provider: course.maNhaCungCap ? `Nhà cung cấp #${course.maNhaCungCap}` : '',
    creator: course.maNhaCungCap ? `Nhà cung cấp #${course.maNhaCungCap}` : '',
    creatorEmail: '',
    price: course.gia == null ? null : Number(course.gia),
    duration: course.thoiLuong,
    submittedAt: course.ngayCapNhat || course.ngayTao,
    status: statusMap[course.trangThaiDuyet] || course.trangThaiDuyet,
    reviewNote: course.lyDoTuChoi || '',
    lectures: (course.baiHocs || []).map((lesson) => ({
      id: String(lesson.maBaiHoc),
      title: lesson.tieuDe || 'Bài học chưa có tiêu đề',
      content: lesson.noiDung || '',
      duration: lesson.thoiLuong,
      attachments: (lesson.taiLieus || []).map((material) => ({
        name: material.tieuDe || 'Tài liệu',
        url: material.duongDanTep || '',
      })),
    })),
    attachments: [],
  }
}

export async function getPendingExpertCourses() {
  const { data } = await api.get('/expert/courses/pending')
  return data.map(mapCourse)
}

export async function getExpertCourse(courseId) {
  const { data } = await api.get(`/expert/courses/${encodeURIComponent(courseId)}`)
  return mapCourse(data)
}

export async function submitExpertCourseDecision(courseId, action, note = '') {
  const decision = { approve: 'APPROVED', reject: 'REJECTED', requestChanges: 'NEEDS_REVISION' }[action]
  if (!decision) throw new Error('Thao tác kiểm duyệt không hợp lệ.')
  const { data } = await api.post(`/expert/courses/${encodeURIComponent(courseId)}/decision`, {
    trangThai: decision,
    ghiChu: note.trim() || null,
    noiDungDanhGia: note.trim() || null,
  })
  return mapCourse(data)
}

export async function getExpertReviewHistory() {
  const { data } = await api.get('/expert/reviews/history')
  return data.map((review) => ({
    id: String(review.maDanhGia),
    title: review.maKhoaHoc ? `Khóa học #${review.maKhoaHoc}` : 'Khóa học',
    creator: '',
    itemType: 'course',
    status: statusMap[review.trangThai] || review.trangThai,
    reviewedAt: review.ngayTao,
    note: review.ghiChu || review.noiDungDanhGia || '',
  }))
}
