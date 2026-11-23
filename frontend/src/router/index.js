import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '@/service/authState'
import { getRoleLandingRouteName, getRoleName, loadCurrentUser } from '@/service/authService'

const routes = [
  {
    path: '/',
    component: () => import('@/layout/UserLayout.vue'),
    meta: { demoOnly: true },
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/user/UserHome.vue'),
        meta: { title: 'EduSuggest – Học tập theo mục tiêu', actor: 'user', demoOnly: true },
      },
      {
        path: 'dashboard',
        name: 'user-dashboard',
        component: () => import('@/views/user/UserDashboard.vue'),
        meta: { title: 'Dashboard người học', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'profile',
        name: 'user-profile',
        component: () => import('@/views/user/UserProfile.vue'),
        meta: { title: 'Hồ sơ cá nhân', actor: 'user', requiresRole: ['USER', 'PROVIDER'] },
      },
      {
        path: 'provider/application',
        name: 'provider-application',
        component: () => import('@/views/user/ProviderApplication.vue'),
        meta: { title: 'Đăng ký trở thành nhà cung cấp', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'courses',
        name: 'course-catalog',
        component: () => import('@/views/user/CourseCatalog.vue'),
        meta: { title: 'Danh sách khóa học', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'courses/:id',
        name: 'course-detail',
        component: () => import('@/views/user/CourseDetail.vue'),
        meta: { title: 'Chi tiết khóa học', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'learning/:courseId',
        name: 'learning',
        component: () => import('@/views/user/LearningView.vue'),
        meta: { title: 'Học khóa học', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'learning-progress',
        name: 'learning-progress',
        component: () => import('@/views/user/LearningProgress.vue'),
        meta: { title: 'Tiến độ học tập', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'learning-history',
        name: 'learning-history',
        component: () => import('@/views/user/LearningHistory.vue'),
        meta: { title: 'Lịch sử học tập', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'materials',
        name: 'material-catalog',
        component: () => import('@/views/user/MaterialCatalog.vue'),
        meta: { title: 'Tài liệu học tập', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'materials/:id',
        name: 'material-detail',
        component: () => import('@/views/user/MaterialDetail.vue'),
        meta: { title: 'Chi tiết tài liệu', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'recommendations/courses',
        name: 'course-recommendations',
        component: () => import('@/views/user/Recommendations.vue'),
        meta: { title: 'Gợi ý khóa học', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'recommendations/materials',
        name: 'material-recommendations',
        component: () => import('@/views/user/Recommendations.vue'),
        meta: { title: 'Gợi ý tài liệu', actor: 'user', requiresRole: 'USER' },
      },
      {
        path: 'expert-reviews',
        name: 'expert-reviews',
        component: () => import('@/views/user/ExpertReviews.vue'),
        meta: { title: 'Đánh giá chuyên gia', actor: 'user', requiresRole: 'USER' },
      },
    ],
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/user/AuthView.vue'),
    meta: { title: 'Đăng ký tài khoản', actor: 'user', publicOnly: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/user/AuthView.vue'),
    meta: { title: 'Đăng nhập', actor: 'user', publicOnly: true },
  },
  {
    path: '/access-denied',
    name: 'access-denied',
    component: () => import('@/views/AccessDeniedView.vue'),
    meta: { title: 'Không có quyền truy cập' },
  },
  ...[
    ['admin', 'ADMIN', 'Không gian quản trị'],
    ['expert', 'EXPERT', 'Không gian chuyên gia'],
    ['provider', 'PROVIDER', 'Không gian nhà cung cấp'],
    ['user', 'USER', 'Không gian người học'],
  ].map(([role, requiredRole, title]) => ({
    path: `/workspace/${role}`,
    name: `workspace-${role}`,
    component: () => import('@/views/RoleLandingView.vue'),
    meta: { title, requiresRole: requiredRole },
  })),
  {
    path: '/admin',
    component: () => import('@/layout/AdminLayout.vue'),
    meta: { requiresRole: 'ADMIN' },
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
        meta: { title: 'Tổng quan quản trị', adminSection: 'Tổng quan', requiresRole: 'ADMIN' },
      },
      {
        path: 'provider-applications',
        name: 'admin-provider-applications',
        component: () => import('@/views/admin/AdminProviderApplications.vue'),
        meta: { title: 'Hồ sơ nhà cung cấp', adminSection: 'Quản lý người dùng', requiresRole: 'ADMIN' },
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
          requiresRole: 'ADMIN',
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
          requiresRole: 'ADMIN',
        },
      })),
      {
        path: 'visibility',
        name: 'admin-visibility',
        component: () => import('@/views/admin/AdminVisibility.vue'),
        meta: { title: 'Trạng thái hiển thị', adminSection: 'Quản lý nội dung', requiresRole: 'ADMIN' },
      },
      {
        path: 'reviewers/assignment',
        name: 'admin-assign-reviewer',
        component: () => import('@/views/admin/AdminReviewerAssignment.vue'),
        meta: { title: 'Phân công Reviewer', adminSection: 'Kiểm duyệt', requiresRole: 'ADMIN' },
      },
      {
        path: 'reviews',
        name: 'admin-review-monitor',
        component: () => import('@/views/admin/AdminReviewMonitor.vue'),
        meta: { title: 'Theo dõi kiểm duyệt', adminSection: 'Kiểm duyệt', requiresRole: 'ADMIN' },
      },
      {
        path: 'recommendations',
        name: 'admin-recommendations',
        component: () => import('@/views/admin/AdminRecommendations.vue'),
        meta: { title: 'Hệ thống gợi ý', adminSection: 'Hệ thống', requiresRole: 'ADMIN' },
      },
      {
        path: 'analytics',
        name: 'admin-analytics',
        component: () => import('@/views/admin/AdminAnalytics.vue'),
        meta: { title: 'Thống kê hệ thống', adminSection: 'Hệ thống', requiresRole: 'ADMIN' },
      },
      {
        path: 'profile',
        name: 'admin-profile',
        component: () => import('@/views/admin/AdminProfile.vue'),
        meta: { title: 'Thông tin cá nhân', adminSection: 'Tài khoản', requiresRole: 'ADMIN' },
      },
    ],
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/views/user/AuthView.vue'),
    meta: { title: 'Đăng nhập quản trị', publicOnly: true },
  },
  {
    path: '/reviewer',
    name: 'reviewer',
    component: () => import('@/layout/ReviewerLayout.vue'),
    meta: { requiresRole: 'EXPERT' },
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
        meta: { title: 'Tổng quan kiểm duyệt', requiresRole: 'EXPERT' },
      },
      {
        path: 'courses',
        name: 'reviewer-courses',
        component: () => import('@/views/reviewer/PendingCourses.vue'),
        meta: { title: 'Khóa học chờ duyệt', requiresRole: 'EXPERT' },
      },
      {
        path: 'courses/:id',
        name: 'reviewer-course-detail',
        component: () => import('@/views/reviewer/CourseReviewDetail.vue'),
        meta: { title: 'Chi tiết kiểm duyệt khóa học', requiresRole: 'EXPERT' },
      },
      {
        path: 'materials',
        name: 'reviewer-materials',
        component: () => import('@/views/reviewer/PendingMaterials.vue'),
        meta: { title: 'Tài liệu chờ duyệt', requiresRole: 'EXPERT' },
      },
      {
        path: 'materials/:id',
        name: 'reviewer-material-detail',
        component: () => import('@/views/reviewer/MaterialReviewDetail.vue'),
        meta: { title: 'Chi tiết kiểm duyệt tài liệu', requiresRole: 'EXPERT' },
      },
      {
        path: 'history',
        name: 'reviewer-history',
        component: () => import('@/views/reviewer/ReviewHistory.vue'),
        meta: { title: 'Lịch sử kiểm duyệt', requiresRole: 'EXPERT' },
      },
      {
        path: 'profile',
        name: 'reviewer-profile',
        component: () => import('@/views/reviewer/ReviewerProfile.vue'),
        meta: { title: 'Hồ sơ cá nhân', requiresRole: 'EXPERT' },
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
    meta: { requiresRole: 'PROVIDER' },
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

router.beforeEach(async (to) => {
  const pageTitle = to.meta.title || 'EduSuggest – Gợi ý học tập thông minh'
  document.title = to.name === 'home' ? pageTitle : `${pageTitle} | EduSuggest`

  if (to.name === 'home') {
    if (!authState.accessToken) return { name: 'login' }

    try {
      const user = await loadCurrentUser()
      return user ? { name: getRoleLandingRouteName(user) } : { name: 'login' }
    } catch (error) {
      const query = {}
      if (error.response?.status !== 401 && authState.accessToken) {
        query.authError = 'unavailable'
      }
      return { name: 'login', query }
    }
  }

  if (to.meta.publicOnly && authState.accessToken && to.query.authError !== 'unavailable') {
    try {
      const user = await loadCurrentUser()
      if (user) return { name: getRoleLandingRouteName(user) }
    } catch (error) {
      if (error.response?.status !== 401 && authState.accessToken) {
        return {
          name: to.name,
          query: { ...to.query, authError: 'unavailable' },
        }
      }
    }
  }

  const requiredRole = to.meta.requiresRole
  if (!requiredRole) return true

  if (!authState.accessToken) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  try {
    await loadCurrentUser()
  } catch (error) {
    const query = { redirect: to.fullPath }
    if (error.response?.status !== 401 && authState.accessToken) {
      query.authError = 'unavailable'
    }
    return {
      name: 'login',
      query,
    }
  }

  const allowedRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole]
  if (!allowedRoles.includes(getRoleName())) {
    return { name: 'access-denied' }
  }
  return true
})

export default router
