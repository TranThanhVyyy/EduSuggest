<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  FileText,
  History,
  PlayCircle,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import CourseCard from '@/components/user/CourseCard.vue'
import CourseProgressCard from '@/components/user/CourseProgressCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { authState } from '@/service/authState'
import {
  fetchMyEnrollments,
  fetchRecommendedCourses,
  fetchRecommendedMaterialsWithMeta,
  fetchUserCategories,
} from '@/service/userApiService'

const router = useRouter()
const userName = computed(() => authState.user?.hoTen?.trim() || '')
const shortUserName = computed(() => {
  const parts = userName.value.split(/\s+/).filter(Boolean)
  if (parts.length <= 2) return parts.join(' ')
  return parts.slice(-2).join(' ')
})

const searchScope = ref('courses')
const searchQuery = ref('')
const searchPlaceholder = computed(() => (
  searchScope.value === 'materials'
    ? 'Tìm tài liệu, giáo trình, bài tập...'
    : 'Tìm khóa học, chủ đề, kỹ năng bạn muốn học...'
))

function clearSearch() {
  searchQuery.value = ''
}

async function submitSearch() {
  const q = searchQuery.value.trim()
  const targetRoute = searchScope.value === 'materials' ? 'material-catalog' : 'course-catalog'
  await router.push({ name: targetRoute, query: q ? { q } : {} })
}

const categoryMap = ref(new Map())

const enrolled = ref([])
const enrollmentsLoading = ref(true)
const enrollmentError = ref('')

const courseRec = ref({ items: [], strategy: 'none', personalized: false })
const courseRecLoading = ref(true)
const courseRecError = ref('')

const materialRec = ref({ items: [], strategy: 'none', personalized: false })
const materialRecLoading = ref(true)
const materialRecError = ref('')

const activeEnrollments = computed(() => {
  return enrolled.value
    .filter((entry) => entry.status !== 'completed' && !entry.completedAt)
    .sort((a, b) => new Date(b.enrolledAt || 0) - new Date(a.enrolledAt || 0))
})

const completedEnrollments = computed(() => {
  return enrolled.value.filter((entry) => entry.status === 'completed' || Boolean(entry.completedAt))
})

const primaryEnrollment = computed(() => activeEnrollments.value[0] || null)
const secondaryEnrollments = computed(() => activeEnrollments.value.slice(1, 4))

const primaryProgress = computed(() => {
  const value = Number(primaryEnrollment.value?.progress ?? 0)
  if (Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
})

const enrichedRecommendedCourses = computed(() => {
  const names = categoryMap.value
  return (courseRec.value.items || []).map((course) => ({
    ...course,
    category: names.get(String(course.categoryId)) || course.category,
  }))
})

const enrichedRecommendedMaterials = computed(() => {
  const names = categoryMap.value
  return (materialRec.value.items || []).map((mat) => ({
    ...mat,
    categoryName: mat.categoryName || names.get(String(mat.categoryId)) || '',
  }))
})

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return ''
  }
}

async function loadCategories() {
  try {
    const list = await fetchUserCategories()
    categoryMap.value = new Map(list.map((item) => [String(item.id), item.name]))
  } catch {
    categoryMap.value = new Map()
  }
}

async function loadEnrollments() {
  enrollmentsLoading.value = true
  enrollmentError.value = ''
  try {
    enrolled.value = await fetchMyEnrollments()
  } catch (error) {
    enrollmentError.value = error.response?.data?.detail || 'Không thể tải danh sách khóa học đã đăng ký.'
  } finally {
    enrollmentsLoading.value = false
  }
}

async function loadCourseRecommendations() {
  courseRecLoading.value = true
  courseRecError.value = ''
  try {
    courseRec.value = await fetchRecommendedCourses({ limit: 6 })
  } catch (error) {
    courseRecError.value = error.response?.data?.detail || 'Không thể tải gợi ý khóa học.'
  } finally {
    courseRecLoading.value = false
  }
}

async function loadMaterialRecommendations() {
  materialRecLoading.value = true
  materialRecError.value = ''
  try {
    materialRec.value = await fetchRecommendedMaterialsWithMeta(null, { limit: 4 })
  } catch (error) {
    materialRecError.value = error.response?.data?.detail || 'Không thể tải gợi ý tài liệu học tập.'
  } finally {
    materialRecLoading.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadEnrollments()
  loadCourseRecommendations()
  loadMaterialRecommendations()
})
</script>

<template>
  <div class="space-y-12 sm:space-y-14">
    <!-- A. EDITORIAL PERSONAL HEADER (No boxed SaaS hero, no KPI stat grid) -->
    <section class="es-hero-enter border-b border-border/80 pb-6 pt-1">
      <div class="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div class="space-y-2">
          <h1 class="ui-page-title text-navy">
            <template v-if="shortUserName">Chào mừng trở lại, {{ shortUserName }}</template>
            <template v-else>Không gian học tập của bạn</template>
          </h1>
          <p v-if="!enrollmentsLoading && !enrollmentError" class="text-sm text-slate-600">
            <template v-if="enrolled.length">
              Bạn đang theo học <strong class="font-semibold text-navy">{{ activeEnrollments.length }} khóa</strong>
              <template v-if="completedEnrollments.length">
                và đã hoàn thành <strong class="font-semibold text-navy">{{ completedEnrollments.length }} khóa</strong>
              </template>
              trên EduSuggest.
            </template>
            <template v-else>
              Bắt đầu bằng việc chọn một khóa học hoặc tài liệu phù hợp với mục tiêu hôm nay của bạn.
            </template>
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5 shrink-0">
          <RouterLink
            :to="{ name: 'course-catalog' }"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          >
            <BookOpen :size="14" class="text-teal" aria-hidden="true" />
            <span>Khám phá khóa học</span>
          </RouterLink>
          <RouterLink
            :to="{ name: 'material-catalog' }"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          >
            <FileText :size="14" class="text-teal" aria-hidden="true" />
            <span>Thư viện tài liệu</span>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- B. CONTINUE LEARNING SPOTLIGHT (Immediate 1-Click Resume) -->
    <section aria-labelledby="continue-learning-heading" class="space-y-5">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span class="ui-tag-label">
            <PlayCircle :size="15" aria-hidden="true" />
            <span>Tiếp tục học</span>
          </span>
          <h2 id="continue-learning-heading" class="ui-section-title mt-1">
            Bài học đang dở của bạn
          </h2>
        </div>

        <RouterLink
          :to="{ name: 'learning-progress' }"
          class="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-teal hover:underline"
        >
          <span>Tất cả khóa học của tôi</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="enrollmentsLoading" class="rounded-2xl border border-border bg-surface p-6">
        <UiSkeleton variant="detail" :lines="4" />
      </div>

      <UiAlert
        v-else-if="enrollmentError"
        variant="danger"
        title="Không thể tải khóa học đang học"
        :message="enrollmentError"
      >
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
          @click="loadEnrollments"
        >
          <RefreshCw :size="13" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      </UiAlert>

      <template v-else-if="primaryEnrollment">
        <!-- Flagship Resume Card -->
        <article class="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
          <div class="grid lg:grid-cols-12">
            <!-- Left: Course Progress & Direct Action -->
            <div class="flex flex-col justify-between gap-6 p-6 sm:p-8 lg:col-span-8">
              <div class="space-y-3">
                <div class="flex flex-wrap items-center gap-2 text-xs">
                  <span class="inline-flex items-center gap-1.5 rounded-full border border-teal/25 bg-teal/10 px-2.5 py-0.5 font-semibold text-teal-dark">
                    <span class="size-1.5 rounded-full bg-teal" aria-hidden="true" />
                    <span>Đang học</span>
                  </span>
                  <span v-if="primaryEnrollment.enrolledAt" class="text-slate-600">
                    Đăng ký {{ formatDate(primaryEnrollment.enrolledAt) }}
                  </span>
                </div>

                <h3 class="font-display text-xl sm:text-2xl font-semibold leading-snug text-navy">
                  <RouterLink
                    :to="{ name: 'course-detail', params: { id: primaryEnrollment.course?.id } }"
                    class="rounded-sm transition-colors duration-150 hover:text-teal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                  >
                    {{ primaryEnrollment.course?.title || 'Khóa học đang tham gia' }}
                  </RouterLink>
                </h3>

                <p v-if="primaryEnrollment.course?.description" class="line-clamp-2 text-sm leading-relaxed text-slate-600">
                  {{ primaryEnrollment.course.description }}
                </p>
              </div>

              <!-- Progress Bar & Actions -->
              <div class="space-y-4">
                <div class="space-y-2">
                  <div class="flex items-center justify-between text-xs font-semibold">
                    <span class="text-slate-600">
                      {{ primaryEnrollment.completedLessons || 0 }} / {{ primaryEnrollment.totalLessons || 0 }} bài học đã hoàn thành
                    </span>
                    <span class="text-navy tabular-nums">{{ primaryProgress }}%</span>
                  </div>
                  <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
                    <div
                      class="h-full rounded-full bg-teal transition-[width] duration-300"
                      :style="{ width: `${primaryProgress}%` }"
                    />
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-3 pt-1">
                  <RouterLink
                    :to="{ name: 'learning', params: { courseId: primaryEnrollment.course?.id } }"
                    class="ui-button ui-button--primary inline-flex items-center gap-2"
                  >
                    <PlayCircle :size="16" aria-hidden="true" />
                    <span>Tiếp tục học ngay</span>
                  </RouterLink>

                  <RouterLink
                    :to="{ name: 'course-detail', params: { id: primaryEnrollment.course?.id } }"
                    class="text-sm font-semibold text-slate-600 transition-colors duration-150 hover:text-navy hover:underline"
                  >
                    Xem chi tiết khóa học
                  </RouterLink>
                </div>
              </div>
            </div>

            <!-- Right: Deep Navy Learning Quick Links Panel -->
            <div class="es-dot-grid flex flex-col justify-between gap-6 border-t border-border bg-navy p-6 text-white sm:p-8 lg:col-span-4 lg:border-l lg:border-t-0">
              <div class="space-y-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-amber">Lộ trình của bạn</p>
                <dl class="grid grid-cols-2 gap-3">
                  <div class="rounded-xl border border-white/10 bg-white/[0.06] p-3">
                    <dt class="text-[11px] text-slate-300">Đang học</dt>
                    <dd class="mt-1 text-2xl font-bold text-white tabular-nums">{{ activeEnrollments.length }}</dd>
                  </div>
                  <div class="rounded-xl border border-white/10 bg-white/[0.06] p-3">
                    <dt class="text-[11px] text-slate-300">Hoàn thành</dt>
                    <dd class="mt-1 text-2xl font-bold text-white tabular-nums">{{ completedEnrollments.length }}</dd>
                  </div>
                </dl>
              </div>

              <div class="space-y-2 border-t border-white/15 pt-4 text-xs">
                <RouterLink
                  :to="{ name: 'learning-history' }"
                  class="flex items-center justify-between rounded-lg px-2.5 py-2 font-medium text-slate-200 transition-colors duration-150 hover:bg-white/10 hover:text-white"
                >
                  <span class="inline-flex items-center gap-2">
                    <History :size="14" class="text-teal-light" aria-hidden="true" />
                    <span>Lịch sử học tập</span>
                  </span>
                  <ArrowRight :size="13" aria-hidden="true" />
                </RouterLink>
                <RouterLink
                  :to="{ name: 'learning-progress' }"
                  class="flex items-center justify-between rounded-lg px-2.5 py-2 font-medium text-slate-200 transition-colors duration-150 hover:bg-white/10 hover:text-white"
                >
                  <span class="inline-flex items-center gap-2">
                    <CheckCircle2 :size="14" class="text-amber" aria-hidden="true" />
                    <span>Quản lý tiến độ</span>
                  </span>
                  <ArrowRight :size="13" aria-hidden="true" />
                </RouterLink>
              </div>
            </div>
          </div>
        </article>

        <!-- Additional Active Courses (if more than 1) -->
        <div v-if="secondaryEnrollments.length" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <CourseProgressCard
            v-for="entry in secondaryEnrollments"
            :key="entry.id"
            :entry="entry"
          />
        </div>
      </template>

      <UiEmptyState
        v-else
        :icon="BookOpen"
        title="Bạn chưa đăng ký khóa học nào"
        description="Khám phá danh mục khóa học đã kiểm duyệt và bắt đầu lộ trình học tập đầu tiên của bạn."
        action-label="Khám phá khóa học"
        :action-route="{ name: 'course-catalog' }"
      />
    </section>

    <!-- B2. QUICK DISCOVERY SEARCH BAND (Bridges Continue Learning -> Recommendations) -->
    <section
      aria-label="Tìm kiếm nhanh khóa học và tài liệu"
      class="rounded-2xl border border-border/80 bg-surface p-5 sm:p-6"
    >
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between lg:gap-8">
        <div class="space-y-1">
          <h2 class="font-display text-base font-semibold text-navy sm:text-lg">
            Tìm nhanh khóa học &amp; tài liệu
          </h2>
          <p class="text-xs text-slate-600 sm:text-sm">
            Tra cứu trực tiếp theo chủ đề, kỹ năng hoặc giáo trình bạn đang quan tâm.
          </p>
        </div>

        <form
          class="group flex w-full items-center gap-1.5 rounded-xl border border-border/90 bg-subtle/75 p-1.5 transition-[background-color,border-color,box-shadow] duration-200 ease-out focus-within:border-teal focus-within:bg-surface focus-within:ring-2 focus-within:ring-teal/15 lg:max-w-xl xl:max-w-2xl"
          role="search"
          @submit.prevent="submitSearch"
        >
          <select
            v-model="searchScope"
            aria-label="Phạm vi tìm kiếm"
            class="h-9 shrink-0 cursor-pointer rounded-lg border border-border/70 bg-surface px-2.5 text-xs font-semibold text-navy outline-none transition-colors duration-150 hover:border-teal/50 focus-visible:border-teal focus-visible:ring-2 focus-visible:ring-teal/25 sm:px-3"
          >
            <option value="courses">Khóa học</option>
            <option value="materials">Tài liệu</option>
          </select>

          <span class="hidden h-5 w-px shrink-0 bg-border/80 sm:block" aria-hidden="true" />

          <label class="relative flex min-w-0 flex-1 items-center gap-2 px-1.5 sm:px-2">
            <span class="sr-only">Tìm kiếm khóa học hoặc tài liệu</span>
            <Search
              :size="16"
              class="shrink-0 text-muted transition-colors duration-150 group-focus-within:text-teal"
              aria-hidden="true"
            />
            <input
              v-model="searchQuery"
              type="search"
              :placeholder="searchPlaceholder"
              class="es-dashboard-search-input h-9 w-full min-w-0 bg-transparent text-sm text-navy placeholder:text-muted/85 outline-none"
            >
          </label>

          <button
            v-if="searchQuery"
            type="button"
            class="flex size-7 shrink-0 items-center justify-center rounded-md text-muted transition-colors duration-150 hover:bg-subtle hover:text-navy focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
            aria-label="Xóa từ khóa tìm kiếm"
            @click="clearSearch"
          >
            <X :size="14" aria-hidden="true" />
          </button>

          <button
            type="submit"
            class="flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-navy px-3 text-xs font-semibold text-white transition-[background-color,transform] duration-150 hover:bg-teal active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40 focus-visible:ring-offset-1 sm:px-4"
            aria-label="Tìm kiếm"
          >
            <Search :size="14" class="sm:hidden" aria-hidden="true" />
            <span class="hidden sm:inline">Tìm kiếm</span>
          </button>
        </form>
      </div>
    </section>

    <!-- C. PERSONALIZED COURSE RECOMMENDATIONS -->
    <section aria-labelledby="recommended-courses-heading" class="space-y-5">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div>
          <span class="ui-tag-label">
            <Sparkles :size="15" aria-hidden="true" />
            <span>{{ courseRec.personalized ? 'Dành riêng cho bạn' : 'Khám phá khóa học' }}</span>
          </span>
          <h2 id="recommended-courses-heading" class="ui-section-title mt-1">
            Khóa học phù hợp tiếp theo
          </h2>
        </div>

        <RouterLink
          :to="{ name: 'course-recommendations' }"
          class="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-teal hover:underline"
        >
          <span>Xem tất cả gợi ý</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="courseRecLoading" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <UiSkeleton v-for="i in 3" :key="i" variant="card" />
      </div>

      <UiAlert
        v-else-if="courseRecError"
        variant="danger"
        title="Không thể tải gợi ý khóa học"
        :message="courseRecError"
      >
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
          @click="loadCourseRecommendations"
        >
          <RefreshCw :size="13" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      </UiAlert>

      <template v-else-if="enrichedRecommendedCourses.length">
        <p
          v-if="courseRec.strategy === 'latest'"
          class="rounded-xl border border-border bg-subtle/70 px-4 py-2.5 text-xs text-slate-600"
          role="status"
        >
          Đang hiển thị các khóa học mới cập nhật. Hoàn thành thêm bài học để hệ thống đề xuất sát hơn với sở thích của bạn.
        </p>

        <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <CourseCard
            v-for="course in enrichedRecommendedCourses.slice(0, 6)"
            :key="course.id"
            :course="course"
          />
        </div>
      </template>

      <UiEmptyState
        v-else
        :icon="Compass"
        title="Chưa có khóa học gợi ý phù hợp"
        description="Hãy khám phá thêm khóa học trong danh mục để hệ thống ghi nhận sở thích học tập của bạn."
        action-label="Mở danh mục khóa học"
        :action-route="{ name: 'course-catalog' }"
      />
    </section>

    <!-- D. INDEPENDENT RECOMMENDED MATERIALS (Distinct Subtle Band) -->
    <section
      aria-labelledby="recommended-materials-heading"
      class="rounded-2xl border border-border/80 bg-subtle/60 p-5 sm:p-8 space-y-5"
    >
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border/80 pb-4">
        <div>
          <span class="ui-tag-label">
            <FileText :size="15" aria-hidden="true" />
            <span>{{ materialRec.personalized ? 'Học liệu phù hợp' : 'Khám phá học liệu' }}</span>
          </span>
          <h2 id="recommended-materials-heading" class="ui-section-title mt-1">
            Tài liệu học tập nên đọc
          </h2>
        </div>

        <RouterLink
          :to="{ name: 'material-recommendations' }"
          class="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-teal hover:underline"
        >
          <span>Xem tất cả tài liệu gợi ý</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="materialRecLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <UiSkeleton v-for="i in 4" :key="i" variant="card" />
      </div>

      <UiAlert
        v-else-if="materialRecError"
        variant="danger"
        title="Không thể tải gợi ý tài liệu"
        :message="materialRecError"
      >
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
          @click="loadMaterialRecommendations"
        >
          <RefreshCw :size="13" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      </UiAlert>

      <UiEmptyState
        v-else-if="!materialRec.hasEnrollments"
        :icon="FileText"
        title="Đăng ký khóa học để nhận gợi ý tài liệu"
        description="Tài liệu đề xuất chỉ được lấy từ khóa học bạn đã đăng ký."
        action-label="Khám phá khóa học"
        :action-route="{ name: 'course-catalog' }"
      />

      <UiAlert
        v-else-if="materialRec.failedCourseCount"
        variant="warning"
        title="Một số tài liệu chưa tải được"
        :message="`Không thể tải gợi ý từ ${materialRec.failedCourseCount} khóa học. Các kết quả đã nhận được vẫn được hiển thị.`"
      />

      <div
        v-if="!materialRecLoading && !materialRecError && materialRec.hasEnrollments && enrichedRecommendedMaterials.length"
        class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        <MaterialCard
          v-for="mat in enrichedRecommendedMaterials.slice(0, 4)"
          :key="mat.id"
          :material="mat"
        />
      </div>

      <UiEmptyState
        v-if="!materialRecLoading && !materialRecError && materialRec.hasEnrollments && !enrichedRecommendedMaterials.length"
        :icon="FileText"
        title="Chưa có tài liệu gợi ý"
        description="Khám phá thư viện tài liệu học tập độc lập để tìm giáo trình và tài liệu tham khảo phù hợp."
        action-label="Mở thư viện tài liệu"
        :action-route="{ name: 'material-catalog' }"
      />
    </section>

    <!-- E. COMPLETED COURSES (Compact Shelf, Only When Present) -->
    <section
      v-if="!enrollmentsLoading && completedEnrollments.length"
      aria-labelledby="completed-courses-heading"
      class="space-y-4 pb-2"
    >
      <div class="flex items-center justify-between border-b border-border pb-3">
        <h2 id="completed-courses-heading" class="ui-section-title">
          Khóa học đã hoàn thành
        </h2>
        <span class="text-xs font-semibold text-slate-600 tabular-nums">
          {{ completedEnrollments.length }} khóa học
        </span>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="entry in completedEnrollments.slice(0, 3)"
          :key="entry.id"
          :to="{ name: 'learning', params: { courseId: entry.course?.id } }"
          class="es-card-interactive group flex items-center justify-between gap-3 rounded-xl border border-border bg-surface p-4 shadow-sm hover:border-teal/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        >
          <div class="flex min-w-0 items-center gap-3">
            <span class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-teal/10 text-teal">
              <CheckCircle2 :size="18" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-navy group-hover:text-teal">
                {{ entry.course?.title || 'Khóa học' }}
              </p>
              <p class="mt-0.5 text-xs text-slate-600">Hoàn thành · Ôn tập lại</p>
            </div>
          </div>
          <ArrowRight :size="15" class="shrink-0 text-slate-500 group-hover:text-teal" aria-hidden="true" />
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.es-dashboard-search-input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}
</style>
