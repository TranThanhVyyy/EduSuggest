export const ADMIN_ROLES = Object.freeze({
  user: 'User',
  reviewer: 'Reviewer',
  provider: 'Course Provider',
  admin: 'Admin',
})

export const adminUsers = [
  { id: 'USR-1001', fullName: 'Nguyễn An Nhiên', email: 'annhien@example.edu', phone: '0901234567', role: ADMIN_ROLES.user, createdAt: '2026-09-10', status: 'active' },
  { id: 'USR-1002', fullName: 'Trần Minh Phúc', email: 'minhphuc@example.edu', phone: '0912345678', role: ADMIN_ROLES.reviewer, createdAt: '2026-08-22', status: 'active' },
  { id: 'USR-1003', fullName: 'Lê Thanh Tùng', email: 'thanhtung@example.edu', phone: '0923456789', role: ADMIN_ROLES.provider, createdAt: '2026-08-03', status: 'active' },
  { id: 'USR-1004', fullName: 'Phạm Thu Hà', email: 'thuha@example.edu', phone: '0934567890', role: ADMIN_ROLES.user, createdAt: '2026-07-14', status: 'locked' },
  { id: 'USR-1005', fullName: 'Võ Hải Yến', email: 'haiyen@example.edu', phone: '0945678901', role: ADMIN_ROLES.reviewer, createdAt: '2026-06-27', status: 'active' },
  { id: 'USR-1006', fullName: 'EduSuggest Admin', email: 'admin@edusuggest.local', phone: '', role: ADMIN_ROLES.admin, createdAt: '2026-01-05', status: 'active', isProtected: true },
]

export const adminReviewers = [
  { id: 'REV-0201', fullName: 'Trần Quốc Bảo', email: 'quocbao@example.edu', expertise: 'Khoa học dữ liệu, Python', joinedAt: '2026-02-18', reviewedCourses: 42, activeAssignments: 2, status: 'active' },
  { id: 'REV-0202', fullName: 'Lê Thu Hà', email: 'thuha@example.edu', expertise: 'Thiết kế, UX/UI', joinedAt: '2026-03-06', reviewedCourses: 35, activeAssignments: 1, status: 'active' },
  { id: 'REV-0203', fullName: 'Nguyễn Minh Anh', email: 'minhanh@example.edu', expertise: 'Công nghệ, Web', joinedAt: '2026-04-12', reviewedCourses: 28, activeAssignments: 3, status: 'active' },
  { id: 'REV-0204', fullName: 'Phạm Đức Long', email: 'duclong@example.edu', expertise: 'Kinh doanh, Agile', joinedAt: '2026-05-01', reviewedCourses: 19, activeAssignments: 0, status: 'locked' },
]

export const adminProviders = [
  { id: 'PRV-0301', name: 'TechMaster Việt Nam', email: 'contact@techmaster.vn', phone: '0241234567', registeredAt: '2026-01-15', publishedCourses: 18, approvedCourses: 14, status: 'active' },
  { id: 'PRV-0302', name: 'FUNiX', email: 'support@funix.edu.vn', phone: '0282345678', registeredAt: '2026-02-11', publishedCourses: 12, approvedCourses: 10, status: 'active' },
  { id: 'PRV-0303', name: 'Nguyễn Hải Yến', email: 'haiyen@example.edu', phone: '0909876543', registeredAt: '2026-04-02', publishedCourses: 3, approvedCourses: 2, status: 'locked' },
]

export const adminCategories = [
  { id: 'CAT-01', name: 'Công nghệ', description: 'Lập trình, dữ liệu và công nghệ thông tin.', createdAt: '2026-01-10', courseCount: 42, status: 'active' },
  { id: 'CAT-02', name: 'Kinh doanh', description: 'Quản trị, kinh doanh và khởi nghiệp.', createdAt: '2026-01-12', courseCount: 28, status: 'active' },
  { id: 'CAT-03', name: 'Thiết kế', description: 'Thiết kế sản phẩm số và trải nghiệm người dùng.', createdAt: '2026-01-17', courseCount: 19, status: 'active' },
  { id: 'CAT-04', name: 'Kỹ năng mềm', description: 'Kỹ năng giao tiếp và phát triển cá nhân.', createdAt: '2026-02-02', courseCount: 14, status: 'inactive' },
]

export const adminCourses = [
  {
    id: 'CRS-3001',
    title: 'Vue.js 3 từ cơ bản đến thực chiến',
    category: 'Công nghệ',
    providerId: 'PRV-0301',
    providerName: 'TechMaster Việt Nam',
    reviewerId: 'REV-0203',
    reviewerName: 'Nguyễn Minh Anh',
    description: 'Khóa học thực hành xây dựng ứng dụng web hiện đại với Vue.js 3 và Composition API.',
    objectives: ['Nắm vững Composition API', 'Xây dựng ứng dụng nhiều trang'],
    audience: 'Người học đã có kiến thức HTML, CSS và JavaScript cơ bản.',
    imageUrl: '',
    submittedAt: '2026-08-12T10:00:00',
    approvedAt: '2026-08-16T15:30:00',
    lessonCount: 18,
    enrollments: 1284,
    reviewStatus: 'DaPheDuyet',
    visibility: 'visible',
  },
  {
    id: 'CRS-3002',
    title: 'Phân tích dữ liệu với Python',
    category: 'Công nghệ',
    providerId: 'PRV-0302',
    providerName: 'FUNiX',
    reviewerId: 'REV-0201',
    reviewerName: 'Trần Quốc Bảo',
    description: 'Làm quen với quy trình phân tích dữ liệu bằng Python, Pandas và Matplotlib.',
    objectives: ['Làm sạch dữ liệu', 'Trình bày kết quả phân tích'],
    audience: 'Sinh viên và người đi làm muốn bắt đầu với phân tích dữ liệu.',
    imageUrl: '',
    submittedAt: '2026-07-22T09:10:00',
    approvedAt: '2026-07-29T13:00:00',
    lessonCount: 24,
    enrollments: 986,
    reviewStatus: 'DaPheDuyet',
    visibility: 'visible',
  },
  {
    id: 'CRS-3003',
    title: 'Tư duy thiết kế sản phẩm số',
    category: 'Thiết kế',
    providerId: 'PRV-0303',
    providerName: 'Nguyễn Hải Yến',
    reviewerId: 'REV-0202',
    reviewerName: 'Lê Thu Hà',
    description: 'Quy trình thiết kế trải nghiệm và giao diện cho sản phẩm số lấy người dùng làm trung tâm.',
    objectives: ['Nghiên cứu người dùng', 'Thiết kế prototype có thể kiểm thử'],
    audience: 'Người mới tìm hiểu UX/UI và thiết kế sản phẩm.',
    imageUrl: '',
    submittedAt: '2026-06-05T11:00:00',
    approvedAt: '2026-06-12T16:20:00',
    lessonCount: 12,
    enrollments: 742,
    reviewStatus: 'DaPheDuyet',
    visibility: 'hidden',
  },
  {
    id: 'CRS-3004',
    title: 'Quản trị dự án Agile',
    category: 'Kinh doanh',
    providerId: 'PRV-0301',
    providerName: 'TechMaster Việt Nam',
    reviewerId: 'REV-0204',
    reviewerName: 'Phạm Đức Long',
    description: 'Các nguyên tắc và thực hành Agile, Scrum giúp nhóm phối hợp và giao hàng hiệu quả.',
    objectives: ['Hiểu vòng đời Scrum', 'Lập kế hoạch sprint'],
    audience: 'Thành viên nhóm sản phẩm và quản lý dự án.',
    imageUrl: '',
    submittedAt: '2026-05-13T08:30:00',
    approvedAt: '2026-05-20T14:00:00',
    lessonCount: 16,
    enrollments: 518,
    reviewStatus: 'DaPheDuyet',
    visibility: 'visible',
  },
]

export const adminLessons = [
  { id: 'LES-4001', title: 'Thiết lập dự án Vue 3', courseId: 'CRS-3001', courseTitle: 'Vue.js 3 từ cơ bản đến thực chiến', chapter: 'Chương 1 · Bắt đầu', order: 1, duration: '32 phút', contentType: 'Văn bản', content: { type: 'text', text: 'Bài học giới thiệu cấu trúc dự án Vue 3 và các bước thiết lập môi trường phát triển.' }, visibility: 'visible', reviewStatus: 'DaPheDuyet' },
  { id: 'LES-4002', title: 'Reactivity và Composition API', courseId: 'CRS-3001', courseTitle: 'Vue.js 3 từ cơ bản đến thực chiến', chapter: 'Chương 2 · Composition API', order: 2, duration: '48 phút', contentType: 'Văn bản', content: null, visibility: 'visible', reviewStatus: 'DaPheDuyet' },
  { id: 'LES-4003', title: 'Làm sạch dữ liệu với Pandas', courseId: 'CRS-3002', courseTitle: 'Phân tích dữ liệu với Python', chapter: 'Chương 2 · Xử lý dữ liệu', order: 5, duration: '45 phút', contentType: 'Video', content: { type: 'video', fileName: 'pandas-cleaning.mp4', fileUrl: '' }, visibility: 'visible', reviewStatus: 'DaPheDuyet' },
  { id: 'LES-4004', title: 'Wireframe đến prototype', courseId: 'CRS-3003', courseTitle: 'Tư duy thiết kế sản phẩm số', chapter: 'Chương 3 · Thiết kế', order: 8, duration: '52 phút', contentType: 'Văn bản', content: null, visibility: 'hidden', reviewStatus: 'DaPheDuyet' },
]

export const adminMaterials = [
  { id: 'MAT-5001', title: 'Sổ tay JavaScript hiện đại', documentType: 'E-book', fileName: 'so-tay-javascript.pdf', mimeType: 'application/pdf', sizeBytes: null, providerId: 'PRV-0301', providerName: 'TechMaster Việt Nam', courseId: 'CRS-3001', courseTitle: 'Vue.js 3 từ cơ bản đến thực chiến', lessonId: 'LES-4001', lessonTitle: 'Thiết lập dự án Vue 3', reviewerId: 'REV-0203', reviewerName: 'Nguyễn Minh Anh', approvedAt: '2026-08-16T15:30:00', fileUrl: '', visibility: 'visible', reviewStatus: 'DaPheDuyet' },
  { id: 'MAT-5002', title: 'Bộ bài tập xác suất thống kê', documentType: 'Bài tập', fileName: 'xac-suat.pdf', mimeType: 'application/pdf', sizeBytes: null, providerId: 'PRV-0302', providerName: 'FUNiX', courseId: '', courseTitle: '', lessonId: '', lessonTitle: '', reviewerId: 'REV-0201', reviewerName: 'Trần Quốc Bảo', approvedAt: '2026-07-29T13:00:00', fileUrl: '', visibility: 'visible', reviewStatus: 'DaPheDuyet' },
  { id: 'MAT-5003', title: 'Tóm tắt nguyên lý UX cơ bản', documentType: 'Slide', fileName: 'ux-principles.pptx', mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', sizeBytes: null, providerId: 'PRV-0303', providerName: 'Nguyễn Hải Yến', courseId: 'CRS-3003', courseTitle: 'Tư duy thiết kế sản phẩm số', lessonId: 'LES-4004', lessonTitle: 'Wireframe đến prototype', reviewerId: 'REV-0202', reviewerName: 'Lê Thu Hà', approvedAt: '2026-06-12T16:20:00', fileUrl: '', visibility: 'hidden', reviewStatus: 'DaPheDuyet' },
]

export const adminProfile = {
  fullName: 'EduSuggest Admin',
  email: 'admin@edusuggest.local',
  phone: '',
  role: ADMIN_ROLES.admin,
  createdAt: '2026-01-05',
}

export const recommendationMetrics = {
  totalSuggestions: 3672,
  usersReached: 2186,
  coursesSuggested: 248,
  materialsSuggested: 386,
  clicks: null,
  interactionRate: null,
  updatedAt: '',
  moduleStatus: 'Chưa kết nối backend',
  byDay: [
    { label: 'T2', value: 320 },
    { label: 'T3', value: 410 },
    { label: 'T4', value: 365 },
    { label: 'T5', value: 520 },
    { label: 'T6', value: 470 },
    { label: 'T7', value: 610 },
    { label: 'CN', value: 477 },
  ],
}

export const analyticsByPeriod = {
  '7d': { users: 1342, reviewers: 12, providers: 86, courses: 4, lessons: 4, materials: 3, enrollments: 4044, visible: 9, hidden: 2, approvals: [4, 6, 3, 8, 5, 9, 7] },
  '30d': { users: 8426, reviewers: 12, providers: 86, courses: 4, lessons: 4, materials: 3, enrollments: 12940, visible: 9, hidden: 2, approvals: [18, 24, 21, 28, 31, 26, 34] },
  '3m': { users: 28410, reviewers: 12, providers: 86, courses: 4, lessons: 4, materials: 3, enrollments: 31860, visible: 9, hidden: 2, approvals: [42, 48, 57, 61, 68, 72, 81] },
  '12m': { users: 98240, reviewers: 12, providers: 86, courses: 4, lessons: 4, materials: 3, enrollments: 124800, visible: 9, hidden: 2, approvals: [83, 91, 104, 118, 127, 139, 151] },
}
