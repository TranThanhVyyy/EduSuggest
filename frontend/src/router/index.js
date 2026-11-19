import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/ExperiencePreview.vue'),
    meta: { title: 'EduSuggest – Gợi ý học tập thông minh' },
  },
  {
    path: '/admin',
    component: () => import('@/layout/AdminLayout.vue'),
    meta: { requiresRole: 'admin' },
    children: [
      {
        path: '',
        name: 'admin-index',
        redirect: { name: 'admin-dashboard' },
      },
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('@/views/admin/AdminDashboard.vue'),
        meta: { title: 'Tổng quan quản trị', adminSection: 'Tổng quan', requiresRole: 'admin' },
      },
      ...[
        ['users', 'admin-users', 'Tài khoản', 'users'],
        ['reviewers', 'admin-reviewers', 'Chuyên gia', 'reviewers'],
        ['providers', 'admin-providers', 'Người cung cấp', 'providers'],
        ['categories', 'admin-categories', 'Danh mục', 'categories'],
        ['courses', 'admin-courses', 'Khóa học', 'courses'],
        ['materials', 'admin-materials', 'Tài liệu', 'materials'],
      ].map(([path, name, title, resource]) => ({
        path,
        name,
        component: () => import('@/views/admin/AdminManagementView.vue'),
        meta: {
          title: `Quản lý ${title.toLocaleLowerCase('vi')}`,
          adminSection: resource === 'users' || resource === 'reviewers' || resource === 'providers'
            ? 'Quản lý người dùng'
            : 'Quản lý nội dung',
          adminResource: resource,
          requiresRole: 'admin',
        },
      })),
      {
        path: 'lessons',
        redirect: { name: 'admin-courses' },
      },
      {
        path: 'roles',
        redirect: { name: 'admin-users' },
      },
      ...[
        ['courses/:id', 'admin-course-detail', 'courses', 'Chi tiết khóa học'],
        ['lessons/:id', 'admin-lesson-detail', 'lessons', 'Chi tiết bài học'],
        ['materials/:id', 'admin-material-detail', 'materials', 'Chi tiết tài liệu'],
      ].map(([path, name, resource, title]) => ({
        path,
        name,
        component: () => import('@/views/admin/AdminContentDetail.vue'),
        meta: {
          title,
          adminSection: 'Quản lý nội dung',
          adminResource: resource,
          requiresRole: 'admin',
        },
      })),
      {
        path: 'visibility',
        name: 'admin-visibility',
        component: () => import('@/views/admin/AdminVisibility.vue'),
        meta: { title: 'Trạng thái hiển thị', adminSection: 'Quản lý nội dung', requiresRole: 'admin' },
      },
      {
        path: 'reviewers/assignment',
        name: 'admin-assign-reviewer',
        component: () => import('@/views/admin/AdminReviewerAssignment.vue'),
        meta: { title: 'Phân công Reviewer', adminSection: 'Kiểm duyệt', requiresRole: 'admin' },
      },
      {
        path: 'reviews',
        name: 'admin-review-monitor',
        component: () => import('@/views/admin/AdminReviewMonitor.vue'),
        meta: { title: 'Theo dõi kiểm duyệt', adminSection: 'Kiểm duyệt', requiresRole: 'admin' },
      },
      {
        path: 'recommendations',
        name: 'admin-recommendations',
        component: () => import('@/views/admin/AdminRecommendations.vue'),
        meta: { title: 'Hệ thống gợi ý', adminSection: 'Hệ thống', requiresRole: 'admin' },
      },
      {
        path: 'analytics',
        name: 'admin-analytics',
        component: () => import('@/views/admin/AdminAnalytics.vue'),
        meta: { title: 'Thống kê hệ thống', adminSection: 'Hệ thống', requiresRole: 'admin' },
      },
      {
        path: 'profile',
        name: 'admin-profile',
        component: () => import('@/views/admin/AdminProfile.vue'),
        meta: { title: 'Thông tin cá nhân', adminSection: 'Tài khoản', requiresRole: 'admin' },
      },
    ],
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/views/admin/AdminLogin.vue'),
    meta: { title: 'Đăng nhập quản trị' },
  },
  {
    path: '/reviewer',
    name: 'reviewer',
    component: () => import('@/layout/ReviewerLayout.vue'),
    meta: { requiresRole: 'reviewer' },
    children: [
      {
        path: '',
        name: 'reviewer-index',
        redirect: { name: 'reviewer-dashboard' },
      },
      {
        path: 'dashboard',
        name: 'reviewer-dashboard',
        component: () => import('@/views/reviewer/ReviewerDashboard.vue'),
        meta: { title: 'Tổng quan kiểm duyệt', requiresRole: 'reviewer' },
      },
      {
        path: 'courses',
        name: 'reviewer-courses',
        component: () => import('@/views/reviewer/PendingCourses.vue'),
        meta: { title: 'Khóa học chờ duyệt', requiresRole: 'reviewer' },
      },
      {
        path: 'courses/:id',
        name: 'reviewer-course-detail',
        component: () => import('@/views/reviewer/CourseReviewDetail.vue'),
        meta: { title: 'Chi tiết kiểm duyệt khóa học', requiresRole: 'reviewer' },
      },
      {
        path: 'materials',
        name: 'reviewer-materials',
        component: () => import('@/views/reviewer/PendingMaterials.vue'),
        meta: { title: 'Tài liệu chờ duyệt', requiresRole: 'reviewer' },
      },
      {
        path: 'materials/:id',
        name: 'reviewer-material-detail',
        component: () => import('@/views/reviewer/MaterialReviewDetail.vue'),
        meta: { title: 'Chi tiết kiểm duyệt tài liệu', requiresRole: 'reviewer' },
      },
      {
        path: 'history',
        name: 'reviewer-history',
        component: () => import('@/views/reviewer/ReviewHistory.vue'),
        meta: { title: 'Lịch sử kiểm duyệt', requiresRole: 'reviewer' },
      },
      {
        path: 'profile',
        name: 'reviewer-profile',
        component: () => import('@/views/reviewer/ReviewerProfile.vue'),
        meta: { title: 'Hồ sơ cá nhân', requiresRole: 'reviewer' },
      },
    ],
  },
  {
    path: '/provider/login',
    name: 'provider-login',
    component: () => import('@/views/provider/ProviderAuthNotice.vue'),
    meta: { title: 'Đăng nhập Provider', demoOnly: true },
  },
  {
    path: '/provider/register',
    name: 'provider-register',
    component: () => import('@/views/provider/ProviderAuthNotice.vue'),
    meta: { title: 'Đăng ký tài khoản', demoOnly: true },
  },
  {
    path: '/provider',
    component: () => import('@/layout/ProviderLayout.vue'),
    meta: { demoOnly: true },
    children: [
      {
        path: '',
        name: 'provider-index',
        redirect: { name: 'provider-dashboard' },
      },
      {
        path: 'dashboard',
        name: 'provider-dashboard',
        component: () => import('@/views/provider/ProviderDashboard.vue'),
        meta: { title: 'Tổng quan Provider', providerSection: 'Tổng quan', demoOnly: true },
      },
      {
        path: 'application',
        redirect: { name: 'provider-register' },
      },
      {
        path: 'profile',
        name: 'provider-profile',
        component: () => import('@/views/provider/ProviderProfile.vue'),
        meta: { title: 'Hồ sơ cá nhân', providerSection: 'Tài khoản', demoOnly: true },
      },
      {
        path: 'courses',
        name: 'provider-courses',
        component: () => import('@/views/provider/ProviderCourseList.vue'),
        meta: { title: 'Khóa học của tôi', providerSection: 'Quản lý khóa học', demoOnly: true },
      },
      {
        path: 'courses/create',
        name: 'provider-course-create',
        component: () => import('@/views/provider/ProviderCourseEditor.vue'),
        meta: { title: 'Tạo khóa học', providerSection: 'Quản lý khóa học', demoOnly: true },
      },
      {
        path: 'courses/:id/edit',
        name: 'provider-course-edit',
        component: () => import('@/views/provider/ProviderCourseEditor.vue'),
        meta: { title: 'Chỉnh sửa khóa học', providerSection: 'Quản lý khóa học', demoOnly: true },
      },
      {
        path: 'courses/:id/submit',
        name: 'provider-review-submit',
        component: () => import('@/views/provider/ProviderCourseEditor.vue'),
        meta: { title: 'Gửi kiểm duyệt', providerSection: 'Kiểm duyệt', providerInitialStep: 4, demoOnly: true },
      },
      {
        path: 'courses/:id/resubmit',
        name: 'provider-resubmit',
        component: () => import('@/views/provider/ProviderCourseEditor.vue'),
        meta: { title: 'Gửi lại kiểm duyệt', providerSection: 'Kiểm duyệt', providerInitialStep: 4, demoOnly: true },
      },
      {
        path: 'courses/:id/lessons',
        name: 'provider-lessons',
        component: () => import('@/views/provider/ProviderLessonManager.vue'),
        meta: { title: 'Chương và bài học', providerSection: 'Quản lý nội dung', demoOnly: true },
      },
      {
        path: 'courses/:id/videos',
        name: 'provider-videos',
        component: () => import('@/views/provider/ProviderAssetManager.vue'),
        meta: { title: 'Video bài học', providerSection: 'Quản lý nội dung', demoOnly: true },
      },
      {
        path: 'courses/:id/materials',
        name: 'provider-materials',
        component: () => import('@/views/provider/ProviderAssetManager.vue'),
        meta: { title: 'Tài liệu khóa học', providerSection: 'Quản lý nội dung', demoOnly: true },
      },
      {
        path: 'courses/:id/feedback',
        name: 'provider-course-feedback',
        component: () => import('@/views/provider/ProviderReviewDetail.vue'),
        meta: { title: 'Phản hồi Reviewer', providerSection: 'Kiểm duyệt', demoOnly: true },
      },
      {
        path: 'courses/:id',
        name: 'provider-course-detail',
        component: () => import('@/views/provider/ProviderCourseDetail.vue'),
        meta: { title: 'Chi tiết khóa học', providerSection: 'Quản lý khóa học', demoOnly: true },
      },
      {
        path: 'reviews',
        name: 'provider-reviews',
        component: () => import('@/views/provider/ProviderReviewList.vue'),
        meta: { title: 'Theo dõi kiểm duyệt', providerSection: 'Kiểm duyệt', demoOnly: true },
      },
      {
        path: 'reviews/history',
        name: 'provider-review-history',
        component: () => import('@/views/provider/ProviderReviewList.vue'),
        meta: { title: 'Lịch sử kiểm duyệt', providerSection: 'Kiểm duyệt', demoOnly: true },
      },
      {
        path: 'reviews/:id',
        name: 'provider-review-detail',
        component: () => import('@/views/provider/ProviderReviewDetail.vue'),
        meta: { title: 'Chi tiết kiểm duyệt', providerSection: 'Kiểm duyệt', demoOnly: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: 'Không tìm thấy trang' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const pageTitle = to.meta.title || 'EduSuggest – Gợi ý học tập thông minh'
  document.title = to.name === 'home' ? pageTitle : `${pageTitle} | EduSuggest`
})

export default router
