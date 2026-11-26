<script setup>
import { computed, ref, watch } from 'vue'
import {
  ArrowLeft,
  BookOpen,
  Check,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  GraduationCap,
  Heart,
  Layers,
  Lock,
  LogIn,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Star,
  Zap,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import {
  enrollUserInCourse,
  fetchMyEnrollments,
  fetchRecommendedMaterialsWithMeta,
  fetchSimilarCourses,
  fetchUserCategories,
  fetchUserCourse,
} from '@/service/userApiService'
import { authState } from '@/service/authState'
import { getRoleName } from '@/service/authService'
import { openMaterialFile } from '@/service/materialFileService'
import { commerceErrorMessage } from '@/service/commerceApiService'
import {
  addCourseToCartSynced,
  commerceState,
  isCourseInCart,
  isCourseWishlisted,
  showCommerceToast,
  syncLearnerCommerceState,
  toggleWishlistCourse,
} from '@/service/commerceState'
import { formatCourseLevel, formatDurationMinutes } from '@/utils/courseDisplay'

const route = useRoute()
const router = useRouter()
const isAuthenticated = computed(() => Boolean(authState.accessToken && authState.user))
const isLearner = computed(() => isAuthenticated.value && getRoleName() === 'USER')
const displayProvider = computed(() => {
  const raw = String(course.value?.provider || '').trim()
  if (!raw || raw === 'Chưa có thông tin' || /^Nhà cung cấp #\d+$/.test(raw)) {
    return 'Thông tin nhà cung cấp chưa được cập nhật'
  }
  return raw
})
const course = ref(null)
const displayLevel = computed(() => formatCourseLevel(course.value?.level))
const estimatedDurationLabel = computed(() => formatDurationMinutes(course.value?.duration) || 'Linh hoạt')
const previewSyllabus = computed(() => {
  if (course.value?.lessons?.length) return course.value.lessons
  return course.value?.publicSyllabus || []
})
const totalLessonCount = computed(() => {
  if (course.value?.lessonCount != null) return course.value.lessonCount
  return previewSyllabus.value.length
})
const lessonsDurationSum = computed(() => {
  const list = previewSyllabus.value
  return list.reduce((sum, l) => {
    const m = Number(String(l?.duration || '').replace(/[^\d]/g, ''))
    return sum + (Number.isFinite(m) ? m : 0)
  }, 0)
})
const loading = ref(false)
const errorMessage = ref('')
const categoryError = ref('')

const enrollment = ref(null)
const enrollmentLoading = ref(false)
const enrollmentError = ref('')
const enrollmentSuccess = ref('')

const cartActionLoading = ref(false)
const wishlistActionLoading = ref(false)

const numericCoursePrice = computed(() => {
  if (course.value?.price === null || course.value?.price === undefined || course.value?.price === '') {
    return null
  }
  const n = Number(course.value.price)
  return Number.isNaN(n) ? null : n
})
const isFreeCourse = computed(() => numericCoursePrice.value === 0)
const isPaidCourse = computed(() => numericCoursePrice.value !== null && numericCoursePrice.value > 0)
const isUnavailablePrice = computed(() => numericCoursePrice.value === null || numericCoursePrice.value < 0)
const inCart = computed(() => (course.value?.id ? isCourseInCart(course.value.id) : false))
const wishlisted = computed(() => (course.value?.id ? isCourseWishlisted(course.value.id) : false))

async function handleAddToCart() {
  if (!course.value || cartActionLoading.value) return
  cartActionLoading.value = true
  enrollmentError.value = ''
  try {
    await addCourseToCartSynced(course.value.id)
  } catch (error) {
    enrollmentError.value = commerceErrorMessage(error, 'Không thể thêm khóa học vào giỏ hàng.')
  } finally {
    cartActionLoading.value = false
  }
}

async function handleToggleWishlist() {
  if (!course.value || wishlistActionLoading.value) return
  wishlistActionLoading.value = true
  enrollmentError.value = ''
  try {
    await toggleWishlistCourse(course.value.id)
  } catch (error) {
    showCommerceToast(commerceErrorMessage(error, 'Không thể cập nhật danh sách yêu thích.'), 'error')
  } finally {
    wishlistActionLoading.value = false
  }
}

function handleBuyNow() {
  if (!course.value) return
  router.push({
    name: 'checkout',
    query: { source: 'BUY_NOW', courseId: String(course.value.id) },
  })
}

const similarCourses = ref([])
const similarLoading = ref(false)
const similarError = ref('')

const relatedMaterials = ref([])
const relatedMaterialsLoading = ref(false)
const relatedMaterialsError = ref('')
const relatedMaterialsForbidden = ref(false)
const openingMaterialId = ref('')

let requestSequence = 0

function formatPrice(price) {
  if (price === null || price === undefined) {
    return 'Chưa có thông tin học phí'
  }
  const numericPrice = Number(price)
  if (isNaN(numericPrice)) {
    return 'Chưa có thông tin học phí'
  }
  return numericPrice > 0
    ? new Intl.NumberFormat('vi-VN').format(numericPrice) + ' ₫'
    : 'Miễn phí'
}

async function openCourseMaterial(material) {
  openingMaterialId.value = String(material.id)
  enrollmentError.value = ''
  try {
    await openMaterialFile({ id: material.id, fileUrl: material.url, title: material.title })
  } catch (cause) {
    enrollmentError.value = cause.response?.data?.detail || 'Không thể mở tài liệu. Hãy kiểm tra trạng thái đăng ký khóa học.'
  } finally {
    openingMaterialId.value = ''
  }
}

async function loadCourse(id) {
  const sequence = ++requestSequence
  course.value = null
  errorMessage.value = ''
  categoryError.value = ''
  enrollmentError.value = ''
  enrollmentSuccess.value = ''
  enrollment.value = null
  enrollmentLoading.value = false
  loading.value = true
  similarCourses.value = []
  similarError.value = ''
  relatedMaterials.value = []
  relatedMaterialsError.value = ''
  relatedMaterialsForbidden.value = false

  try {
    const courseData = await fetchUserCourse(id)
    if (sequence !== requestSequence) return
    course.value = courseData

    // Check enrollment status (only for authenticated USER)
    if (isLearner.value) {
      try {
        const enrollments = await fetchMyEnrollments()
        if (sequence !== requestSequence) return
        enrollment.value = enrollments.find((item) => String(item.course?.id) === String(id)) || null
      } catch {
        enrollment.value = null
      }
    }

    // Load category name
    try {
      const categories = await fetchUserCategories()
      if (sequence !== requestSequence) return
      const categoryName = categories.find((cat) => String(cat.id) === String(courseData.categoryId))?.name
      if (categoryName) {
        course.value = { ...courseData, category: categoryName }
      }
    } catch {
      // Silent fallback
    }

    // Load personalized similar courses & related course materials only when authenticated USER
    if (isLearner.value) {
      await Promise.all([
        loadSimilar(id, sequence),
        enrollment.value ? loadRelatedMaterials(id, sequence) : Promise.resolve(),
      ])
    }
  } catch (error) {
    if (sequence !== requestSequence) return
    errorMessage.value = error.response?.data?.detail || 'Không thể tải thông tin khóa học. Vui lòng thử lại.'
  } finally {
    if (sequence === requestSequence) {
      loading.value = false
    }
  }
}

async function loadRelatedMaterials(courseId, parentSequence) {
  relatedMaterialsLoading.value = true
  relatedMaterialsError.value = ''
  relatedMaterialsForbidden.value = false
  try {
    const result = await fetchRecommendedMaterialsWithMeta(courseId, { limit: 6 })
    if (parentSequence !== requestSequence) return
    relatedMaterials.value = (result.items || []).map((item) => ({
      ...item,
      courseTitle: course.value?.title || '',
      lessonTitle: item.lessonId ? `Mã bài học: ${item.lessonId}` : '',
    }))
  } catch (cause) {
    if (parentSequence !== requestSequence) return
    if (cause.response?.status === 403) {
      relatedMaterialsForbidden.value = true
      relatedMaterialsError.value = cause.response?.data?.detail || 'Bạn cần đăng ký khóa học để truy cập tài liệu liên quan.'
    } else {
      relatedMaterialsError.value = cause.response?.data?.detail || 'Không thể tải tài liệu học tập liên quan.'
    }
  } finally {
    if (parentSequence === requestSequence) {
      relatedMaterialsLoading.value = false
    }
  }
}

async function loadSimilar(courseId, parentSequence) {
  similarLoading.value = true
  similarError.value = ''
  try {
    const result = await fetchSimilarCourses(courseId, { limit: 3 })
    if (parentSequence !== requestSequence) return
    similarCourses.value = result.filter((item) => String(item.id) !== String(courseId))
  } catch (cause) {
    if (parentSequence !== requestSequence) return
    similarError.value = cause.response?.data?.detail || 'Không thể tải khóa học tương tự.'
  } finally {
    if (parentSequence === requestSequence) {
      similarLoading.value = false
    }
  }
}

async function enroll() {
  if (!course.value || enrollmentLoading.value || enrollment.value) return
  const current = requestSequence
  const courseId = course.value.id
  enrollmentLoading.value = true
  enrollmentError.value = ''
  enrollmentSuccess.value = ''

  try {
    const result = await enrollUserInCourse(courseId)
    if (current !== requestSequence) return
    enrollment.value = result
    enrollmentSuccess.value = 'Đăng ký khóa học thành công! Bạn có thể bắt đầu học ngay bây giờ.'
    syncLearnerCommerceState({ force: true })

    try {
      const refreshed = await fetchUserCourse(courseId)
      if (current === requestSequence) {
        course.value = refreshed
      }
    } catch {
      // Keep existing data
    }
    await loadRelatedMaterials(courseId, current)
  } catch (error) {
    if (current !== requestSequence) return
    enrollmentError.value = error.response?.data?.detail || 'Không thể đăng ký khóa học. Hãy kiểm tra kết nối và thử lại.'
  } finally {
    if (current === requestSequence) {
      enrollmentLoading.value = false
    }
  }
}

watch(() => route.params.id, (id) => {
  if (id) loadCourse(id)
}, { immediate: true })
</script>

<template>
  <div class="space-y-8">
    <!-- Top breadcrumb -->
    <nav aria-label="Điều hướng" class="flex min-w-0 items-center gap-2 text-xs font-semibold text-muted">
      <RouterLink :to="{ name: 'course-catalog' }" class="inline-flex shrink-0 items-center gap-1.5 text-teal hover:underline">
        <ArrowLeft :size="14" aria-hidden="true" />
        <span>Danh sách khóa học</span>
      </RouterLink>
      <span class="shrink-0">/</span>
      <span class="min-w-0 flex-1 truncate text-ink">{{ course?.title || 'Chi tiết khóa học' }}</span>
    </nav>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="grid gap-8 lg:grid-cols-[1fr_360px]">
      <div class="space-y-6">
        <UiSkeleton variant="text" :lines="2" />
        <UiSkeleton variant="image" height="240px" />
        <UiSkeleton variant="text" :lines="4" />
      </div>
      <div>
        <UiSkeleton variant="card" />
      </div>
    </div>

    <!-- Error State -->
    <UiAlert
      v-else-if="errorMessage"
      variant="danger"
      title="Không thể tải khóa học"
      :message="errorMessage"
      class="max-w-2xl"
    >
      <button
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadCourse(route.params.id)"
      >
        <RefreshCw :size="14" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <!-- Loaded Course Content -->
    <div v-else-if="course" class="grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1fr)_360px] items-start">
      <!-- LEFT COLUMN: Main Course Information & Curriculum -->
      <main class="min-w-0 space-y-8">
        <!-- Header Info -->
        <header class="space-y-3">
          <div class="flex flex-wrap items-center gap-2">
            <span
              v-if="course.category"
              class="inline-flex items-center rounded-md bg-navy px-2.5 py-0.5 text-xs font-semibold text-white"
            >
              {{ course.category }}
            </span>
            <span
              v-if="displayLevel"
              class="inline-flex items-center rounded-md bg-subtle px-2.5 py-0.5 text-xs font-medium text-ink border border-border"
            >
              {{ displayLevel }}
            </span>
          </div>

          <h1 class="ui-page-title text-navy">
            {{ course.title }}
          </h1>

          <p class="whitespace-pre-line text-sm sm:text-base leading-relaxed text-muted">
            {{ course.description || 'Khóa học chưa có mô tả chi tiết từ nhà cung cấp.' }}
          </p>

          <!-- Quick specs bar -->
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 border-t border-border/80">
            <div class="bento-card p-3">
              <span class="text-[11px] font-semibold text-muted uppercase">Nhà cung cấp</span>
              <p class="mt-0.5 text-xs font-bold text-navy truncate">
                {{ displayProvider }}
              </p>
            </div>

            <div class="bento-card p-3">
              <span class="text-[11px] font-semibold text-muted uppercase">Thời lượng học ước tính</span>
              <p class="mt-0.5 text-xs font-bold text-navy">
                {{ estimatedDurationLabel }}
              </p>
              <p v-if="lessonsDurationSum > 0" class="mt-0.5 text-[11px] text-muted">
                Tổng bài giảng: {{ lessonsDurationSum }} phút
              </p>
            </div>

            <div class="bento-card p-3 col-span-2 sm:col-span-1">
              <span class="text-[11px] font-semibold text-muted uppercase">Nội dung</span>
              <p class="mt-0.5 text-xs font-bold text-navy">
                {{ totalLessonCount }} bài giảng
              </p>
            </div>
          </div>
        </header>

        <!-- Course Curriculum / Syllabus Section -->
        <section aria-label="Đề cương khóa học" class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="ui-section-title">
              Nội dung chương trình học
            </h2>
            <span class="text-xs font-semibold text-muted">
              {{ totalLessonCount }} bài học
            </span>
          </div>

          <!-- If Enrolled: Full access with lesson list and materials -->
          <div v-if="enrollment" class="space-y-3">
            <div
              v-for="(lesson, index) in course.lessons"
              :key="lesson.id"
              class="bento-card p-4 transition-colors"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex items-start gap-3">
                  <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-teal/10 text-xs font-bold text-teal">
                    {{ index + 1 }}
                  </span>

                  <div>
                    <h3 class="text-sm font-bold text-navy">
                      {{ lesson.title }}
                    </h3>
                    <p v-if="lesson.duration" class="mt-0.5 text-xs text-muted">
                      Thời lượng: {{ lesson.duration }}
                    </p>
                  </div>
                </div>

                <span class="rounded bg-teal/10 px-2 py-0.5 text-[11px] font-semibold text-teal">
                  Đã mở khóa
                </span>
              </div>

              <!-- Lesson text snippet -->
              <p v-if="lesson.content" class="mt-3 whitespace-pre-line text-xs leading-relaxed text-muted border-t border-border/60 pt-2.5">
                {{ lesson.content }}
              </p>

              <!-- Attached Materials -->
              <div v-if="lesson.materials && lesson.materials.length" class="mt-3 space-y-1.5 border-t border-border/60 pt-2.5">
                <span class="text-[11px] font-semibold text-muted uppercase">Tài liệu đính kèm:</span>
                <ul class="space-y-1">
                  <li
                    v-for="mat in lesson.materials"
                    :key="mat.id"
                    class="flex items-center justify-between text-xs"
                  >
                    <span class="flex items-center gap-1.5 text-ink">
                      <FileText :size="13" class="text-teal" aria-hidden="true" />
                      <span class="truncate max-w-[240px]">{{ mat.title }}</span>
                    </span>
                    <button
                      v-if="mat.url"
                      type="button"
                      :disabled="openingMaterialId === String(mat.id)"
                      class="text-teal font-medium hover:underline inline-flex items-center gap-1"
                      @click="openCourseMaterial(mat)"
                    >
                      <span>{{ openingMaterialId === String(mat.id) ? 'Đang mở…' : 'Mở tài liệu' }}</span>
                      <ExternalLink :size="11" aria-hidden="true" />
                    </button>
                  </li>
                </ul>
              </div>
            </div>

            <p v-if="!course.lessons || !course.lessons.length" class="text-sm text-muted py-4">
              Khóa học này hiện đang được nhà cung cấp hoàn thiện nội dung bài học.
            </p>
          </div>

          <!-- If Not Enrolled: Preview Syllabus with lock state -->
          <div v-else class="space-y-3">
            <div
              v-for="(lesson, index) in previewSyllabus"
              :key="lesson.id"
              class="bento-card p-3.5 flex items-center justify-between gap-3 opacity-95"
            >
              <div class="flex min-w-0 items-center gap-3">
                <span class="flex size-7 shrink-0 items-center justify-center rounded-full bg-subtle text-xs font-bold text-muted">
                  {{ index + 1 }}
                </span>
                <div class="min-w-0">
                  <span class="block text-sm font-semibold text-navy truncate">
                    {{ lesson.title }}
                  </span>
                  <span v-if="lesson.duration" class="block text-[11px] text-muted">
                    {{ formatDurationMinutes(lesson.duration) }}
                  </span>
                </div>
              </div>
              <span class="inline-flex shrink-0 items-center gap-1 rounded-md bg-subtle px-2 py-0.5 text-xs font-medium text-muted">
                <Lock :size="12" aria-hidden="true" />
                <span>Khóa</span>
              </span>
            </div>

            <div class="rounded-xl border border-dashed border-border bg-subtle/50 p-4 text-center">
              <p class="text-xs text-muted leading-relaxed">
                Đăng ký khóa học để mở quyền truy cập đầy đủ toàn bộ video bài giảng và tài liệu học tập đính kèm.
              </p>
            </div>
          </div>
        </section>

        <!-- Related Learning Materials Section -->
        <section aria-label="Tài liệu học tập liên quan" class="space-y-4 border-t border-border pt-6">
          <div class="flex items-center justify-between gap-2">
            <div>
              <span class="ui-tag-label">
                <FileText :size="15" aria-hidden="true" />
                <span>Học liệu bổ trợ</span>
              </span>
              <h2 class="ui-section-title mt-1">Tài liệu học tập liên quan</h2>
            </div>
          </div>

          <div
            v-if="!enrollment"
            class="rounded-xl border border-dashed border-border bg-subtle/50 p-5 text-center"
          >
            <p class="inline-flex items-center gap-1.5 text-sm font-semibold text-navy">
              <Lock :size="15" class="text-muted" aria-hidden="true" />
              <span>Tài liệu dành riêng cho học viên đã đăng ký</span>
            </p>
            <p class="mt-1 text-xs leading-relaxed text-muted">
              Đăng ký khóa học để xem danh sách tài liệu học tập liên quan đã được chuyên gia phê duyệt.
            </p>
          </div>

          <div v-else-if="relatedMaterialsLoading" class="grid gap-4 sm:grid-cols-2">
            <UiSkeleton v-for="i in 2" :key="i" variant="card" />
          </div>

          <UiAlert
            v-else-if="relatedMaterialsError"
            :variant="relatedMaterialsForbidden ? 'warning' : 'danger'"
            :title="relatedMaterialsForbidden ? 'Chưa có quyền truy cập tài liệu' : 'Không thể tải tài liệu liên quan'"
            :message="relatedMaterialsError"
          >
            <button
              v-if="!relatedMaterialsForbidden"
              type="button"
              class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
              @click="loadRelatedMaterials(course.id, requestSequence)"
            >
              <RefreshCw :size="13" aria-hidden="true" />
              <span>Thử lại</span>
            </button>
          </UiAlert>

          <div v-else-if="relatedMaterials.length" class="grid gap-4 sm:grid-cols-2">
            <MaterialCard
              v-for="mat in relatedMaterials"
              :key="mat.id"
              :material="mat"
            />
          </div>

          <UiEmptyState
            v-else
            :icon="FileText"
            title="Chưa có tài liệu liên quan"
            description="Khóa học này hiện chưa có tài liệu học tập liên quan đã được phê duyệt hiển thị."
          />
        </section>

        <!-- Similar Courses Recommendation -->
        <section v-if="isLearner" aria-labelledby="similar-courses-heading" class="space-y-4 border-t border-border pt-6">
          <div class="flex items-center justify-between">
            <div>
              <span class="ui-tag-label">
                <Sparkles :size="15" aria-hidden="true" />
                <span>Nội dung tương tự</span>
              </span>
              <h2 id="similar-courses-heading" class="ui-section-title mt-1">Khóa học tương tự</h2>
            </div>
          </div>

          <div v-if="similarLoading" class="grid gap-4 sm:grid-cols-2" role="status" aria-label="Đang tải khóa học tương tự">
            <UiSkeleton v-for="i in 2" :key="i" variant="card" />
          </div>

          <UiAlert
            v-else-if="similarError"
            variant="danger"
            title="Không thể tải khóa học tương tự"
            :message="similarError"
          >
            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
              @click="loadSimilar(course.id, requestSequence)"
            >
              <RefreshCw :size="13" aria-hidden="true" />
              <span>Thử lại</span>
            </button>
          </UiAlert>

          <div v-else-if="similarCourses.length" class="grid gap-4 sm:grid-cols-2">
            <CourseCard
              v-for="item in similarCourses"
              :key="item.id"
              :course="item"
            />
          </div>

          <UiEmptyState
            v-else
            :icon="BookOpen"
            title="Chưa có khóa học tương tự"
            description="Backend hiện chưa tìm thấy khóa học phù hợp với nội dung này."
          />
        </section>
      </main>

      <!-- RIGHT COLUMN: Sticky Enrollment Action Card -->
      <aside class="min-w-0 sticky top-6 space-y-4">
        <div class="bento-card overflow-hidden p-0 shadow-md">
          <!-- Thumbnail cover -->
          <div class="aspect-video w-full bg-subtle overflow-hidden">
            <img
              v-if="course.coverImageUrl"
              :src="course.coverImageUrl"
              :alt="course.title"
              class="h-full w-full object-cover"
            >
            <div v-else class="flex h-full w-full flex-col items-center justify-center bg-navy text-white p-6 text-center">
              <GraduationCap :size="48" class="text-teal mb-2" aria-hidden="true" />
              <span class="font-bold text-sm tracking-wide">EduSuggest Course</span>
            </div>
          </div>

          <!-- Body details & action -->
          <div class="p-5 space-y-5">
            <!-- Price and Enrollment status -->
            <div class="flex items-baseline justify-between">
              <div>
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-600">Học phí</span>
                <p class="text-2xl font-bold text-navy">
                  {{ formatPrice(course.price) }}
                </p>
              </div>

              <UiStatusBadge
                v-if="enrollment"
                status="dang_hoc"
                label="Đã đăng ký"
              />
            </div>

            <!-- Feedback alerts -->
            <UiAlert
              v-if="enrollmentSuccess"
              variant="success"
              :message="enrollmentSuccess"
            />
            <UiAlert
              v-if="enrollmentError"
              variant="danger"
              :message="enrollmentError"
            />

            <!-- Primary Action Buttons -->
            <div class="space-y-2.5">
              <RouterLink
                v-if="enrollment"
                :to="{ name: 'learning', params: { courseId: course.id } }"
                class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <PlayCircle :size="16" aria-hidden="true" />
                <span>Tiếp tục học ngay</span>
              </RouterLink>

              <RouterLink
                v-else-if="!isAuthenticated"
                :to="{ name: 'login', query: { redirect: route.fullPath } }"
                class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <LogIn :size="16" aria-hidden="true" />
                <span>{{ isPaidCourse && commerceState.marketplaceEnabled ? 'Đăng nhập để mua khóa học' : 'Đăng nhập để đăng ký khóa học' }}</span>
              </RouterLink>

              <!-- Marketplace Commerce Flow (when Marketplace is enabled on server) -->
              <template v-else-if="commerceState.marketplaceEnabled && isLearner">
                <button
                  v-if="isUnavailablePrice"
                  type="button"
                  disabled
                  class="ui-button ui-button--outline w-full inline-flex items-center justify-center gap-2 opacity-65 cursor-not-allowed"
                >
                  <Lock :size="15" aria-hidden="true" />
                  <span>Chưa khả dụng để mua</span>
                </button>

                <button
                  v-else-if="isFreeCourse"
                  type="button"
                  class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
                  :disabled="enrollmentLoading"
                  @click="enroll"
                >
                  <RefreshCw v-if="enrollmentLoading" :size="16" class="animate-spin" aria-hidden="true" />
                  <BookOpen v-else :size="16" aria-hidden="true" />
                  <span>{{ enrollmentLoading ? 'Đang xử lý đăng ký…' : 'Đăng ký học miễn phí' }}</span>
                </button>

                <template v-else-if="isPaidCourse">
                  <button
                    type="button"
                    class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
                    @click="handleBuyNow"
                  >
                    <Zap :size="16" aria-hidden="true" />
                    <span>Mua ngay</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <RouterLink
                      v-if="inCart"
                      :to="{ name: 'cart' }"
                      class="ui-button ui-button--outline flex-1 inline-flex items-center justify-center gap-2 active:scale-[0.98]"
                    >
                      <ShoppingCart :size="15" class="text-teal" aria-hidden="true" />
                      <span>Đi tới giỏ hàng</span>
                    </RouterLink>
                    <button
                      v-else
                      type="button"
                      class="ui-button ui-button--outline flex-1 inline-flex items-center justify-center gap-2 active:scale-[0.98]"
                      :disabled="cartActionLoading"
                      @click="handleAddToCart"
                    >
                      <RefreshCw v-if="cartActionLoading" :size="15" class="animate-spin" aria-hidden="true" />
                      <ShoppingCart v-else :size="15" aria-hidden="true" />
                      <span>{{ cartActionLoading ? 'Đang thêm…' : 'Thêm vào giỏ hàng' }}</span>
                    </button>

                    <button
                      type="button"
                      class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface text-navy transition-[background-color,border-color,transform] duration-150 hover:border-teal/50 hover:bg-subtle active:scale-[0.95] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
                      :aria-pressed="wishlisted"
                      :aria-label="wishlisted ? 'Bỏ khỏi danh sách yêu thích' : 'Lưu vào danh sách yêu thích'"
                      :title="wishlisted ? 'Bỏ yêu thích' : 'Lưu vào yêu thích'"
                      :disabled="wishlistActionLoading"
                      @click="handleToggleWishlist"
                    >
                      <Heart
                        :size="17"
                        :class="wishlisted ? 'fill-rose-500 text-rose-500' : 'text-navy'"
                        aria-hidden="true"
                      />
                    </button>
                  </div>
                </template>
              </template>

              <!-- Legacy Direct Enrollment Flow (when Marketplace is not active on Production) -->
              <button
                v-else
                type="button"
                class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
                :disabled="enrollmentLoading"
                @click="enroll"
              >
                <RefreshCw v-if="enrollmentLoading" :size="16" class="animate-spin" aria-hidden="true" />
                <BookOpen v-else :size="16" aria-hidden="true" />
                <span>{{ enrollmentLoading ? 'Đang xử lý đăng ký…' : 'Đăng ký khóa học này' }}</span>
              </button>
            </div>

            <!-- Value propositions checklist -->
            <div class="border-t border-border pt-4 space-y-2 text-xs text-muted">
              <div class="flex items-center gap-2 text-ink">
                <Check :size="14" class="text-teal shrink-0" aria-hidden="true" />
                <span>Truy cập trọn đời các bài giảng</span>
              </div>
              <div class="flex items-center gap-2 text-ink">
                <Check :size="14" class="text-teal shrink-0" aria-hidden="true" />
                <span>Đề xuất tài liệu đính kèm thông minh</span>
              </div>
              <div class="flex items-center gap-2 text-ink">
                <Check :size="14" class="text-teal shrink-0" aria-hidden="true" />
                <span>Tự động lưu lại tiến trình học tập</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
