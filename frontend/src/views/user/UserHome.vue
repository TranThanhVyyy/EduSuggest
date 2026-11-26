<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Code2,
  Compass,
  Cpu,
  Database,
  FileText,
  Globe,
  GraduationCap,
  Layers,
  Lock,
  LogIn,
  Palette,
  Search,
  Sparkles,
  UserPlus,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { authState } from '@/service/authState'
import { getRoleLandingRouteName, getRoleName } from '@/service/authService'
import {
  fetchPublicMaterials,
  fetchUserCategories,
  fetchUserCourses,
} from '@/service/userApiService'

const router = useRouter()

const isAuthenticated = computed(() => Boolean(authState.accessToken && authState.user))
const isLearner = computed(() => getRoleName() === 'USER')
const dashboardRouteName = computed(() => getRoleLandingRouteName())

const heroQuery = ref('')
const heroScope = ref('courses') // 'courses' | 'materials'

const categories = ref([])
const totalCategories = ref(null)
const categoriesLoading = ref(false)
const categoriesRequiresAuth = ref(false)

const courses = ref([])
const allCourses = ref([])
const totalCourses = ref(null)
const coursesLoading = ref(false)
const coursesError = ref('')
const coursesRequiresAuth = ref(false)

const materials = ref([])
const totalMaterials = ref(null)
const materialsLoading = ref(false)
const materialsError = ref('')
const materialsRequiresAuth = ref(false)

const spotlightCourse = computed(() => courses.value[0] || null)
const spotlightMaterial = computed(() => materials.value[0] || null)

const DEFAULT_VISIBLE_CATEGORIES = 8
const categoriesExpanded = ref(false)

const courseCountByCategory = computed(() => {
  const counts = new Map()
  for (const c of allCourses.value) {
    if (c.categoryId != null) {
      const key = String(c.categoryId)
      counts.set(key, (counts.get(key) || 0) + 1)
    }
  }
  return counts
})

const sortedCategories = computed(() => {
  const counts = courseCountByCategory.value
  return [...categories.value].sort((a, b) => {
    const countDiff = (counts.get(String(b.id)) || 0) - (counts.get(String(a.id)) || 0)
    if (countDiff !== 0) return countDiff
    return String(a.name || '').localeCompare(String(b.name || ''), 'vi')
  })
})

const visibleCategories = computed(() =>
  categoriesExpanded.value
    ? sortedCategories.value
    : sortedCategories.value.slice(0, DEFAULT_VISIBLE_CATEGORIES),
)

const hasMoreCategories = computed(
  () => sortedCategories.value.length > DEFAULT_VISIBLE_CATEGORIES,
)

const hiddenCategoryCount = computed(() =>
  Math.max(0, sortedCategories.value.length - DEFAULT_VISIBLE_CATEGORIES),
)

function getCategoryIcon(category) {
  const name = String(category?.name || '').toLocaleLowerCase('vi')
  if (/trí tuệ nhân tạo|ai\b|machine learning|học máy|deep learning/.test(name)) return Cpu
  if (/dữ liệu|data|phân tích|thống kê|analytics/.test(name)) return BarChart3
  if (/cơ sở dữ liệu|database|sql|điện toán|cloud|hệ thống|mạng|bảo mật/.test(name)) return Database
  if (/lập trình|code|phần mềm|web|frontend|backend|mobile|python|java/.test(name)) return Code2
  if (/thiết kế|ui|ux|đồ họa|sáng tạo|design/.test(name)) return Palette
  if (/kinh doanh|quản trị|marketing|tài chính|kế toán|khởi nghiệp/.test(name)) return Briefcase
  if (/ngoại ngữ|tiếng anh|ngôn ngữ|giao tiếp|ielts|toeic/.test(name)) return Globe
  if (/kỹ năng|học thuật|toán|khoa học|giáo dục/.test(name)) return BookOpen
  return Compass
}

function submitHeroSearch() {
  const q = heroQuery.value.trim()
  const target = heroScope.value === 'materials' ? 'material-catalog' : 'course-catalog'
  router.push({ name: target, query: q ? { q } : {} })
}

async function loadPublicContent() {
  categoriesLoading.value = true
  coursesLoading.value = true
  materialsLoading.value = true
  coursesError.value = ''
  materialsError.value = ''
  categoriesRequiresAuth.value = false
  coursesRequiresAuth.value = false
  materialsRequiresAuth.value = false

  const [catRes, courseRes, matRes] = await Promise.allSettled([
    fetchUserCategories(),
    fetchUserCourses(),
    fetchPublicMaterials({ page: 1, pageSize: 4 }),
  ])

  const catNames = new Map()
  if (catRes.status === 'fulfilled') {
    categories.value = catRes.value
    totalCategories.value = catRes.value.length
    for (const c of catRes.value) catNames.set(String(c.id), c.name)
  } else {
    const status = catRes.reason?.response?.status
    if (status === 401 || status === 403) categoriesRequiresAuth.value = true
    totalCategories.value = null
    categories.value = []
  }
  categoriesLoading.value = false

  if (courseRes.status === 'fulfilled') {
    const mapped = courseRes.value.map((c) => ({
      ...c,
      category: catNames.get(String(c.categoryId)) || c.category,
    }))
    allCourses.value = mapped
    totalCourses.value = mapped.length
    courses.value = mapped.slice(0, 6)
  } else {
    const status = courseRes.reason?.response?.status
    if (status === 401 || status === 403) {
      coursesRequiresAuth.value = true
    } else {
      coursesError.value = courseRes.reason?.response?.data?.detail || 'Không thể tải danh sách khóa học.'
    }
    allCourses.value = []
    totalCourses.value = null
    courses.value = []
  }
  coursesLoading.value = false

  if (matRes.status === 'fulfilled') {
    const items = matRes.value?.items || []
    totalMaterials.value = Number(matRes.value?.total ?? items.length)
    materials.value = items.slice(0, 4).map((m) => ({
      ...m,
      categoryName: m.categoryName || catNames.get(String(m.categoryId)) || '',
    }))
  } else {
    const status = matRes.reason?.response?.status
    if (status === 401 || status === 403) {
      materialsRequiresAuth.value = true
    } else {
      materialsError.value = matRes.reason?.response?.data?.detail || 'Không thể tải danh sách tài liệu học tập.'
    }
    totalMaterials.value = null
    materials.value = []
  }
  materialsLoading.value = false
}

// Subtle scroll-reveal for below-the-fold sections (graceful fallback + respects reduced motion)
const revealedSections = ref(new Set())
const sectionEls = new Map()
let observer = null

function registerSection(key) {
  return (el) => {
    if (el) {
      sectionEls.set(key, el)
      if (observer) observer.observe(el)
    } else {
      sectionEls.delete(key)
    }
  }
}

onMounted(() => {
  loadPublicContent()

  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
    revealedSections.value = new Set(['categories', 'courses', 'materials', 'about', 'cta'])
    return
  }

  const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (prefersReduced) {
    revealedSections.value = new Set(['categories', 'courses', 'materials', 'about', 'cta'])
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const key = entry.target.getAttribute('data-reveal-key')
          if (key) {
            revealedSections.value = new Set([...revealedSections.value, key])
          }
          observer?.unobserve(entry.target)
        }
      }
    },
    { rootMargin: '0px 0px -48px 0px', threshold: 0.05 },
  )

  for (const el of sectionEls.values()) {
    observer.observe(el)
  }
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<template>
  <div class="space-y-14 sm:space-y-20">
    <!-- B. HERO SECTION – Editorial EdTech Modernism + Interactive Bento Showcase -->
    <section class="relative border-b border-border/80 pb-12 pt-2 sm:pb-16 sm:pt-6">
      <div class="grid gap-8 sm:gap-10 lg:grid-cols-12 lg:items-center">
        <!-- Left Column: Editorial Headline, Search & Actions -->
        <div class="es-hero-enter min-w-0 space-y-6 lg:col-span-7">
          <div class="space-y-4">
            <span class="inline-flex max-w-full items-center gap-2 rounded-full border border-teal/25 bg-teal/10 px-3 py-1 text-xs font-semibold text-teal-dark">
              <Sparkles :size="14" class="shrink-0" aria-hidden="true" />
              <span class="truncate">Nền tảng gợi ý khóa học &amp; tài liệu học tập</span>
            </span>

            <h1 class="ui-display-title text-[1.75rem] leading-[1.18] tracking-tight text-navy sm:text-4xl lg:text-[2.75rem] break-words">
              Học đúng điều bạn cần.
              <span class="block text-teal underline decoration-teal/25 decoration-2 underline-offset-8">
                Phát triển theo cách của bạn.
              </span>
            </h1>

            <p class="max-w-xl text-sm sm:text-base leading-relaxed text-slate-600">
              EduSuggest giúp bạn khám phá khóa học có kiểm duyệt chuyên gia và thư viện tài liệu học tập mở, kết hợp gợi ý cá nhân hóa theo mục tiêu học tập.
            </p>
          </div>

          <!-- Elevated Search Bar -->
          <form
            class="flex min-w-0 flex-col gap-2 rounded-2xl border border-border bg-surface p-2 shadow-md transition-colors duration-150 sm:flex-row sm:items-center focus-within:border-teal focus-within:ring-2 focus-within:ring-teal/15"
            role="search"
            @submit.prevent="submitHeroSearch"
          >
            <div class="flex items-center gap-1 rounded-xl bg-subtle p-1 shrink-0">
              <button
                type="button"
                :aria-pressed="heroScope === 'courses'"
                :class="[
                  'flex-1 sm:flex-none rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors duration-150 active:scale-[0.97]',
                  heroScope === 'courses' ? 'bg-navy text-white shadow-sm' : 'text-slate-600 hover:text-navy',
                ]"
                @click="heroScope = 'courses'"
              >
                Khóa học
              </button>
              <button
                type="button"
                :aria-pressed="heroScope === 'materials'"
                :class="[
                  'flex-1 sm:flex-none rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors duration-150 active:scale-[0.97]',
                  heroScope === 'materials' ? 'bg-navy text-white shadow-sm' : 'text-slate-600 hover:text-navy',
                ]"
                @click="heroScope = 'materials'"
              >
                Tài liệu
              </button>
            </div>

            <label class="relative min-w-0 flex-1">
              <Search :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden="true" />
              <input
                v-model="heroQuery"
                type="search"
                placeholder="Bạn muốn học điều gì hôm nay?"
                aria-label="Tìm kiếm khóa học hoặc tài liệu"
                class="w-full min-w-0 bg-transparent py-2 pl-9 pr-3 text-sm text-navy placeholder:text-muted outline-none"
              >
            </label>

            <button type="submit" class="ui-button ui-button--primary shrink-0 rounded-xl">
              Tìm kiếm
            </button>
          </form>

          <!-- Primary & Secondary CTAs -->
          <div class="flex flex-wrap items-center gap-3 pt-1">
            <RouterLink :to="{ name: 'course-catalog' }" class="ui-button ui-button--primary inline-flex items-center gap-2">
              <BookOpen :size="15" aria-hidden="true" />
              <span>Khám phá khóa học</span>
            </RouterLink>

            <RouterLink :to="{ name: 'material-catalog' }" class="ui-button ui-button--outline inline-flex items-center gap-2">
              <FileText :size="15" class="text-teal" aria-hidden="true" />
              <span>Tìm tài liệu học tập</span>
            </RouterLink>
          </div>
        </div>

        <!-- Right Column: Live Editorial Bento Showcase (100% Real API Data) -->
        <aside
          aria-label="Tổng quan thư viện tri thức EduSuggest"
          class="es-hero-enter-delay min-w-0 grid gap-3.5 lg:col-span-5"
        >
          <!-- Top Bento Tile: Deep Navy Live Library Metrics -->
          <div class="es-dot-grid min-w-0 rounded-2xl border border-navy/15 bg-navy p-4 sm:p-5 text-white shadow-md">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="inline-flex min-w-0 items-center gap-2 text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-slate-300">
                <span class="size-2 shrink-0 rounded-full bg-amber" aria-hidden="true" />
                <span class="truncate">Thư viện học thuật mở</span>
              </span>
              <span class="shrink-0 rounded-md bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-teal-light">
                Đã kiểm duyệt
              </span>
            </div>

            <div class="mt-4 grid grid-cols-3 gap-2 sm:gap-2.5">
              <div class="min-w-0 rounded-xl border border-white/10 bg-white/[0.06] p-2.5 sm:p-3">
                <span class="block truncate text-[11px] font-medium text-slate-300">Danh mục</span>
                <span
                  class="mt-1 block text-xl sm:text-2xl font-bold text-white tabular-nums"
                  :aria-label="categoriesLoading ? 'Đang tải danh mục' : totalCategories === null ? 'Dữ liệu danh mục tạm thời không khả dụng' : `${totalCategories} danh mục`"
                >
                  {{ categoriesLoading ? '…' : totalCategories === null ? '—' : totalCategories }}
                </span>
              </div>

              <div class="min-w-0 rounded-xl border border-white/10 bg-white/[0.06] p-2.5 sm:p-3">
                <span class="block truncate text-[11px] font-medium text-slate-300">Khóa học</span>
                <span
                  class="mt-1 block text-xl sm:text-2xl font-bold text-white tabular-nums"
                  :aria-label="coursesLoading ? 'Đang tải khóa học' : totalCourses === null ? 'Dữ liệu khóa học tạm thời không khả dụng' : `${totalCourses} khóa học`"
                >
                  {{ coursesLoading ? '…' : totalCourses === null ? '—' : totalCourses }}
                </span>
              </div>

              <div class="min-w-0 rounded-xl border border-white/10 bg-white/[0.06] p-2.5 sm:p-3">
                <span class="block truncate text-[11px] font-medium text-slate-300">Tài liệu</span>
                <span
                  class="mt-1 block text-xl sm:text-2xl font-bold text-white tabular-nums"
                  :aria-label="materialsLoading ? 'Đang tải tài liệu' : totalMaterials === null ? 'Dữ liệu tài liệu tạm thời không khả dụng' : `${totalMaterials} tài liệu`"
                >
                  {{ materialsLoading ? '…' : totalMaterials === null ? '—' : totalMaterials }}
                </span>
              </div>
            </div>
          </div>

          <!-- Bottom Split Bento Tiles: Live Course & Material Spotlights -->
          <div class="grid gap-3.5 sm:grid-cols-2">
            <!-- Live Spotlight Course -->
            <RouterLink
              v-if="spotlightCourse"
              :to="{ name: 'course-detail', params: { id: spotlightCourse.id } }"
              class="es-card-interactive group flex flex-col justify-between rounded-2xl border border-border bg-surface p-4 shadow-sm hover:border-teal/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            >
              <div>
                <div class="flex items-center justify-between gap-2">
                  <span class="inline-flex items-center gap-1 rounded-md bg-navy/5 px-2 py-0.5 text-[11px] font-semibold text-navy">
                    <BookOpen :size="12" class="text-teal" aria-hidden="true" />
                    <span>Khóa học tiêu biểu</span>
                  </span>
                  <ArrowUpRight :size="15" class="text-slate-500 transition-colors duration-150 group-hover:text-teal" aria-hidden="true" />
                </div>
                <p class="mt-2.5 line-clamp-2 text-sm font-bold leading-snug text-navy group-hover:text-teal">
                  {{ spotlightCourse.title }}
                </p>
              </div>
              <p class="mt-3 truncate text-xs text-slate-600">
                {{ spotlightCourse.category || spotlightCourse.level || 'Xem chi tiết khóa học' }}
              </p>
            </RouterLink>

            <div
              v-else-if="coursesLoading"
              class="rounded-2xl border border-border bg-surface p-4"
            >
              <UiSkeleton variant="text" :lines="3" />
            </div>

            <RouterLink
              v-else
              :to="{ name: 'course-catalog' }"
              class="es-card-interactive group flex flex-col justify-between rounded-2xl border border-border bg-surface p-4 shadow-sm hover:border-teal/40"
            >
              <span class="inline-flex size-9 items-center justify-center rounded-xl bg-navy/5 text-navy">
                <BookOpen :size="18" aria-hidden="true" />
              </span>
              <div class="mt-3">
                <p class="text-sm font-bold text-navy group-hover:text-teal">Danh mục khóa học</p>
                <p class="mt-0.5 text-xs text-slate-600">Duyệt toàn bộ khóa học công khai</p>
              </div>
            </RouterLink>

            <!-- Live Spotlight Material -->
            <RouterLink
              v-if="spotlightMaterial"
              :to="{ name: 'material-detail', params: { id: spotlightMaterial.id } }"
              class="es-card-interactive group flex flex-col justify-between rounded-2xl border border-teal/20 bg-teal/[0.04] p-4 shadow-sm hover:border-teal/45 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            >
              <div>
                <div class="flex items-center justify-between gap-2">
                  <span class="inline-flex items-center gap-1 rounded-md bg-teal/10 px-2 py-0.5 text-[11px] font-semibold text-teal-dark">
                    <FileText :size="12" aria-hidden="true" />
                    <span>{{ spotlightMaterial.type || 'Tài liệu' }}</span>
                  </span>
                  <ArrowUpRight :size="15" class="text-teal-dark" aria-hidden="true" />
                </div>
                <p class="mt-2.5 line-clamp-2 text-sm font-bold leading-snug text-navy group-hover:text-teal">
                  {{ spotlightMaterial.title }}
                </p>
              </div>
              <p class="mt-3 truncate text-xs text-slate-600">
                {{ spotlightMaterial.categoryName || 'Tài liệu học tập mở' }}
              </p>
            </RouterLink>

            <div
              v-else-if="materialsLoading"
              class="rounded-2xl border border-border bg-surface p-4"
            >
              <UiSkeleton variant="text" :lines="3" />
            </div>

            <RouterLink
              v-else
              :to="{ name: 'material-catalog' }"
              class="es-card-interactive group flex flex-col justify-between rounded-2xl border border-teal/20 bg-teal/[0.04] p-4 shadow-sm hover:border-teal/45"
            >
              <span class="inline-flex size-9 items-center justify-center rounded-xl bg-teal/15 text-teal-dark">
                <FileText :size="18" aria-hidden="true" />
              </span>
              <div class="mt-3">
                <p class="text-sm font-bold text-navy group-hover:text-teal">Thư viện tài liệu</p>
                <p class="mt-0.5 text-xs text-slate-600">Tra cứu giáo trình &amp; học liệu mở</p>
              </div>
            </RouterLink>
          </div>
        </aside>
      </div>
    </section>

    <!-- C. EXPLORE CATEGORIES -->
    <section
      :ref="registerSection('categories')"
      data-reveal-key="categories"
      aria-labelledby="categories-heading"
      :class="['es-reveal space-y-5', { 'es-reveal--visible': revealedSections.has('categories') }]"
    >
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border/70 pb-4">
        <div>
          <span class="ui-tag-label">
            <Layers :size="15" aria-hidden="true" />
            <span>Chủ đề học tập</span>
          </span>
          <h2 id="categories-heading" class="ui-section-title mt-1">Khám phá theo danh mục</h2>
          <p class="mt-1 text-sm text-slate-600">
            Chọn lĩnh vực bạn quan tâm để lọc nhanh các khóa học phù hợp.
          </p>
        </div>

        <RouterLink
          :to="{ name: 'course-catalog' }"
          class="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-teal transition-colors duration-150 hover:bg-teal/5 hover:text-teal-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal sm:text-sm"
        >
          <span>Tất cả khóa học</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="categoriesLoading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <UiSkeleton v-for="i in 8" :key="i" variant="rect" height="60px" rounded="0.75rem" />
      </div>

      <div v-else-if="sortedCategories.length" class="space-y-4">
        <TransitionGroup
          name="es-cat-grid"
          tag="div"
          id="homepage-categories-grid"
          class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
        >
          <RouterLink
            v-for="cat in visibleCategories"
            :key="cat.id"
            :to="{ name: 'course-catalog', query: { category_id: cat.id } }"
            :title="cat.name"
            class="group flex items-center justify-between gap-2.5 rounded-xl border border-border/80 bg-surface px-3.5 py-3 transition-colors duration-150 hover:border-teal/45 hover:bg-subtle/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
          >
            <div class="flex min-w-0 items-center gap-2.5">
              <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-teal/10 text-teal transition-colors duration-150 group-hover:bg-teal group-hover:text-white">
                <component :is="getCategoryIcon(cat)" :size="15" aria-hidden="true" />
              </span>
              <div class="min-w-0">
                <span class="block truncate text-[13.5px] font-semibold leading-snug text-navy transition-colors duration-150 group-hover:text-teal">
                  {{ cat.name }}
                </span>
                <span
                  v-if="totalCourses !== null"
                  class="block text-xs text-muted tabular-nums"
                >
                  {{ courseCountByCategory.get(String(cat.id)) ?? 0 }} khóa học
                </span>
              </div>
            </div>
            <ChevronRight :size="14" class="shrink-0 text-slate-400 transition-colors duration-150 group-hover:text-teal" aria-hidden="true" />
          </RouterLink>
        </TransitionGroup>

        <div v-if="hasMoreCategories" class="flex justify-center pt-1">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-4 py-2 text-xs font-semibold text-navy transition-colors duration-150 hover:border-teal/40 hover:bg-subtle hover:text-teal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            aria-controls="homepage-categories-grid"
            :aria-expanded="categoriesExpanded"
            :aria-label="categoriesExpanded ? 'Thu gọn danh sách danh mục về 8 mục nổi bật' : `Xem thêm ${hiddenCategoryCount} danh mục học tập`"
            @click="categoriesExpanded = !categoriesExpanded"
          >
            <span>{{ categoriesExpanded ? 'Thu gọn' : `Xem thêm danh mục (${hiddenCategoryCount})` }}</span>
            <ChevronUp v-if="categoriesExpanded" :size="15" aria-hidden="true" />
            <ChevronDown v-else :size="15" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div
        v-else-if="categoriesRequiresAuth"
        class="rounded-xl border border-dashed border-border bg-subtle/50 p-5 text-sm text-slate-600 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div class="flex items-start gap-2.5">
          <Lock :size="16" class="mt-0.5 shrink-0 text-slate-500" aria-hidden="true" />
          <span>Vui lòng đăng nhập tài khoản học viên để xem đầy đủ danh mục học tập.</span>
        </div>
        <RouterLink v-if="!isAuthenticated" :to="{ name: 'login' }" class="ui-button ui-button--outline ui-button--sm shrink-0">
          Đăng nhập để xem
        </RouterLink>
      </div>

      <UiEmptyState
        v-else
        :icon="Layers"
        title="Chưa có danh mục học tập"
        description="Hệ thống chưa có danh mục công khai nào để hiển thị."
      />
    </section>

    <!-- D. FEATURED COURSES -->
    <section
      :ref="registerSection('courses')"
      data-reveal-key="courses"
      aria-labelledby="featured-courses-heading"
      :class="['es-reveal space-y-5', { 'es-reveal--visible': revealedSections.has('courses') }]"
    >
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div>
          <span class="ui-tag-label">
            <BookOpen :size="15" aria-hidden="true" />
            <span>Khóa học</span>
          </span>
          <h2 id="featured-courses-heading" class="ui-section-title mt-1">Khóa học nổi bật</h2>
          <p class="mt-1 text-sm text-slate-600">Lộ trình học tập có đề cương bài bản, đã được chuyên gia kiểm duyệt.</p>
        </div>

        <RouterLink
          :to="{ name: 'course-catalog' }"
          class="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-teal hover:underline"
        >
          <span>Xem tất cả khóa học</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="coursesLoading" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <UiSkeleton v-for="i in 3" :key="i" variant="card" />
      </div>

      <UiAlert
        v-else-if="coursesError"
        variant="danger"
        title="Không thể tải khóa học"
        :message="coursesError"
      />

      <div
        v-else-if="coursesRequiresAuth"
        class="rounded-xl border border-dashed border-border bg-subtle/50 p-6 text-center space-y-3"
      >
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-navy">
          <Lock :size="16" class="text-slate-500" aria-hidden="true" />
          <span>Đăng nhập để duyệt danh sách khóa học công khai</span>
        </p>
        <p class="mx-auto max-w-lg text-xs leading-relaxed text-slate-600">
          Vui lòng đăng nhập hoặc tạo tài khoản học viên để duyệt toàn bộ khóa học đã được chuyên gia kiểm duyệt.
        </p>
        <div v-if="!isAuthenticated" class="flex flex-wrap justify-center gap-2 pt-1">
          <RouterLink :to="{ name: 'login' }" class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5">
            <LogIn :size="14" aria-hidden="true" />
            <span>Đăng nhập</span>
          </RouterLink>
          <RouterLink :to="{ name: 'register' }" class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5">
            <UserPlus :size="14" aria-hidden="true" />
            <span>Đăng ký</span>
          </RouterLink>
        </div>
      </div>

      <div v-else-if="courses.length" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <CourseCard v-for="course in courses" :key="course.id" :course="course" />
      </div>

      <UiEmptyState
        v-else
        :icon="BookOpen"
        title="Chưa có khóa học công khai"
        description="Hiện chưa có khóa học nào được xuất bản hiển thị công khai."
      />
    </section>

    <!-- E. LEARNING MATERIALS (Distinct Independent Library Band) -->
    <section
      :ref="registerSection('materials')"
      data-reveal-key="materials"
      aria-labelledby="public-materials-heading"
      :class="['es-reveal rounded-2xl border border-border/80 bg-subtle/60 p-5 sm:p-8 space-y-5', { 'es-reveal--visible': revealedSections.has('materials') }]"
    >
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border/80 pb-4">
        <div>
          <span class="ui-tag-label">
            <FileText :size="15" aria-hidden="true" />
            <span>Thư viện học liệu độc lập</span>
          </span>
          <h2 id="public-materials-heading" class="ui-section-title mt-1">Tài liệu học tập nổi bật</h2>
          <p class="mt-1 text-sm text-slate-600">Giáo trình, slide, bài tập và tài liệu tham khảo tách biệt với khóa học để bạn tra cứu linh hoạt.</p>
        </div>

        <RouterLink
          :to="{ name: 'material-catalog' }"
          class="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-teal hover:underline"
        >
          <span>Khám phá tất cả tài liệu</span>
          <ArrowRight :size="14" aria-hidden="true" />
        </RouterLink>
      </div>

      <div v-if="materialsLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <UiSkeleton v-for="i in 4" :key="i" variant="card" />
      </div>

      <UiAlert
        v-else-if="materialsError"
        variant="danger"
        title="Không thể tải tài liệu học tập"
        :message="materialsError"
      />

      <div
        v-else-if="materialsRequiresAuth"
        class="rounded-xl border border-dashed border-border bg-surface p-6 text-center space-y-3"
      >
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-navy">
          <Lock :size="16" class="text-slate-500" aria-hidden="true" />
          <span>Đăng nhập để duyệt thư viện tài liệu học tập</span>
        </p>
        <p class="mx-auto max-w-lg text-xs leading-relaxed text-slate-600">
          Vui lòng đăng nhập tài khoản học viên để tra cứu và tải các tài liệu đã được chuyên gia phê duyệt.
        </p>
      </div>

      <div v-else-if="materials.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MaterialCard v-for="mat in materials" :key="mat.id" :material="mat" />
      </div>

      <UiEmptyState
        v-else
        :icon="FileText"
        title="Chưa có tài liệu công khai"
        description="Hiện chưa có tài liệu học tập nào được xuất bản hiển thị công khai."
      />
    </section>

    <!-- F. WHY EDUSUGGEST – 3-Pillar Editorial Bento Grid -->
    <section
      :ref="registerSection('about')"
      data-reveal-key="about"
      aria-labelledby="why-edusuggest-heading"
      :class="['es-reveal space-y-6', { 'es-reveal--visible': revealedSections.has('about') }]"
    >
      <div class="max-w-2xl">
        <span class="ui-tag-label">
          <Layers :size="15" aria-hidden="true" />
          <span>Giá trị cốt lõi</span>
        </span>
        <h2 id="why-edusuggest-heading" class="ui-section-title mt-1">Một nền tảng, ba giá trị cốt lõi</h2>
        <p class="mt-1.5 text-sm text-slate-600">
          Thiết kế dành riêng cho việc khám phá nội dung học thuật minh bạch và nâng cao hiệu quả tự học.
        </p>
      </div>

      <div class="grid gap-5 md:grid-cols-3">
        <!-- Pillar 01: Courses -->
        <article class="flex flex-col justify-between gap-5 rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <div class="space-y-3.5">
            <div class="flex items-center justify-between">
              <span class="inline-flex size-10 items-center justify-center rounded-xl bg-teal/10 text-teal">
                <BookOpen :size="20" aria-hidden="true" />
              </span>
              <span class="font-mono text-xs font-semibold text-slate-500">01</span>
            </div>
            <h3 class="text-base font-bold text-navy">Khám phá khóa học có kiểm duyệt</h3>
            <p class="text-sm leading-relaxed text-slate-600">
              Mỗi khóa học đều trải qua quy trình đánh giá chuyên môn trước khi hiển thị công khai, đảm bảo cấu trúc bài giảng mạch lạc và minh bạch về trình độ, thời lượng.
            </p>
          </div>
          <div class="flex flex-wrap gap-2 border-t border-border/70 pt-4">
            <span class="inline-flex items-center gap-1.5 rounded-full bg-subtle px-2.5 py-1 text-xs font-medium text-ink">
              <CheckCircle2 :size="13" class="text-teal" aria-hidden="true" />
              <span>Kiểm duyệt chuyên gia</span>
            </span>
            <span class="inline-flex items-center gap-1.5 rounded-full bg-subtle px-2.5 py-1 text-xs font-medium text-ink">
              <CheckCircle2 :size="13" class="text-teal" aria-hidden="true" />
              <span>Lộ trình rõ ràng</span>
            </span>
          </div>
        </article>

        <!-- Pillar 02: Independent Materials -->
        <article class="flex flex-col justify-between gap-5 rounded-2xl border border-border bg-subtle/70 p-6">
          <div class="space-y-3.5">
            <div class="flex items-center justify-between">
              <span class="inline-flex size-10 items-center justify-center rounded-xl border border-border/70 bg-surface text-teal shadow-sm">
                <FileText :size="20" aria-hidden="true" />
              </span>
              <span class="font-mono text-xs font-semibold text-slate-500">02</span>
            </div>
            <h3 class="text-base font-bold text-navy">Thư viện tài liệu học tập độc lập</h3>
            <p class="text-sm leading-relaxed text-slate-600">
              Tra cứu nhanh giáo trình, slide, bài tập và mã nguồn theo danh mục hoặc định dạng mà không bị ràng buộc phải đăng ký khóa học trước.
            </p>
          </div>
          <div class="flex flex-wrap gap-2 border-t border-border/70 pt-4">
            <span class="inline-flex items-center gap-1.5 rounded-full bg-surface px-2.5 py-1 text-xs font-medium text-ink border border-border/60">
              <CheckCircle2 :size="13" class="text-teal" aria-hidden="true" />
              <span>Đa dạng định dạng</span>
            </span>
            <span class="inline-flex items-center gap-1.5 rounded-full bg-surface px-2.5 py-1 text-xs font-medium text-ink border border-border/60">
              <CheckCircle2 :size="13" class="text-teal" aria-hidden="true" />
              <span>Tra cứu linh hoạt</span>
            </span>
          </div>
        </article>

        <!-- Pillar 03: Deep Navy Anchor – Learning Progress -->
        <article class="es-dot-grid flex flex-col justify-between gap-5 rounded-2xl border border-navy/15 bg-navy p-6 text-white shadow-sm">
          <div class="space-y-3.5">
            <div class="flex items-center justify-between">
              <span class="inline-flex size-10 items-center justify-center rounded-xl bg-amber/20 text-amber">
                <GraduationCap :size="20" aria-hidden="true" />
              </span>
              <span class="font-mono text-xs font-semibold text-slate-400">03</span>
            </div>
            <h3 class="text-base font-bold text-white">Đồng hành trọn vẹn quá trình học</h3>
            <p class="text-sm leading-relaxed text-slate-300">
              Đăng nhập tài khoản để đăng ký khóa học, theo dõi phần trăm hoàn thành từng bài giảng, lưu lịch sử học tập và mở khóa tài liệu chuyên sâu gắn kèm bài học.
            </p>
          </div>
          <div class="flex flex-wrap gap-2 border-t border-white/15 pt-4">
            <span class="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-xs font-medium text-teal-light">
              <CheckCircle2 :size="13" class="text-amber" aria-hidden="true" />
              <span>Theo dõi tiến độ</span>
            </span>
            <span class="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-xs font-medium text-teal-light">
              <CheckCircle2 :size="13" class="text-amber" aria-hidden="true" />
              <span>Lưu lịch sử học tập</span>
            </span>
          </div>
        </article>
      </div>
    </section>

    <!-- G. CALL TO ACTION – Distinct Editorial Deep Navy Banner -->
    <section
      :ref="registerSection('cta')"
      data-reveal-key="cta"
      :class="['es-reveal pb-4 sm:pb-6', { 'es-reveal--visible': revealedSections.has('cta') }]"
    >
      <div class="es-dot-grid rounded-2xl border border-navy/15 bg-navy p-7 sm:p-12 text-white shadow-md">
        <div class="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div class="max-w-2xl space-y-2.5">
            <p class="text-xs font-bold uppercase tracking-wider text-amber">Bắt đầu cùng EduSuggest</p>
            <h2 class="font-display text-2xl sm:text-3xl font-semibold tracking-tight text-white">
              Sẵn sàng mở rộng hành trình tri thức của bạn?
            </h2>
            <p class="text-sm sm:text-base leading-relaxed text-slate-300">
              Khám phá ngay danh sách khóa học và thư viện tài liệu mở, hoặc tạo tài khoản học viên để nhận gợi ý cá nhân hóa.
            </p>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center shrink-0">
            <RouterLink :to="{ name: 'course-catalog' }" class="ui-button ui-button--accent inline-flex items-center justify-center gap-2">
              <BookOpen :size="15" aria-hidden="true" />
              <span>Khám phá khóa học</span>
            </RouterLink>
            <RouterLink
              :to="{ name: 'material-catalog' }"
              class="ui-button border border-white/25 bg-white/10 text-white hover:bg-white/20 inline-flex items-center justify-center gap-2"
            >
              <FileText :size="15" aria-hidden="true" />
              <span>Khám phá tài liệu</span>
            </RouterLink>
          </div>
        </div>

        <div class="mt-6 flex flex-wrap items-center gap-4 border-t border-white/15 pt-5 text-xs text-slate-300">
          <template v-if="!isAuthenticated">
            <span>Muốn lưu tiến độ và nhận gợi ý cá nhân hóa?</span>
            <RouterLink :to="{ name: 'register' }" class="font-semibold text-teal-light hover:underline">
              Tạo tài khoản miễn phí →
            </RouterLink>
            <RouterLink :to="{ name: 'login' }" class="font-semibold text-white hover:underline">
              Đăng nhập
            </RouterLink>
          </template>
          <RouterLink
            v-else
            :to="{ name: dashboardRouteName }"
            class="inline-flex items-center gap-1.5 font-semibold text-teal-light hover:underline"
          >
            <span>{{ isLearner ? 'Đi tới không gian học tập của tôi' : 'Đi tới không gian làm việc' }}</span>
            <ArrowRight :size="14" aria-hidden="true" />
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.es-cat-grid-enter-active,
.es-cat-grid-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.es-cat-grid-enter-from,
.es-cat-grid-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

@media (prefers-reduced-motion: reduce) {
  .es-cat-grid-enter-active,
  .es-cat-grid-leave-active {
    transition: none;
  }

  .es-cat-grid-enter-from,
  .es-cat-grid-leave-to {
    transform: none;
  }
}
</style>
