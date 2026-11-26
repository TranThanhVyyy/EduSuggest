<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BookOpen, RefreshCw, RotateCcw, Search, SlidersHorizontal, X } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { fetchUserCategories, fetchUserCourses } from '@/service/userApiService'

const route = useRoute()
const router = useRouter()
const pageSize = 6
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const category = ref(typeof route.query.category_id === 'string' ? route.query.category_id : '')
const level = ref('')
const price = ref('')
const sortBy = ref('title')
const currentPage = ref(1)
const mobileFilterOpen = ref(false)
const mobileFilterTriggerRef = ref(null)
const mobileFilterCloseRef = ref(null)

const courses = ref([])
const categoryOptions = ref([])
let categoriesLoaded = false
const loading = ref(true)
const errorMessage = ref('')
const categoryError = ref('')

const categories = computed(() => categoryOptions.value)
const levels = computed(() => [...new Set(courses.value.map((course) => course.level).filter(Boolean))].sort())

let searchTimer
let requestSequence = 0

async function loadCatalog(loadCategories = false) {
  const sequence = ++requestSequence
  loading.value = true
  errorMessage.value = ''
  const courseRequest = fetchUserCourses({ query: query.value, categoryId: category.value })
  const categoryRequest = loadCategories || !categoriesLoaded
    ? fetchUserCategories()
    : Promise.resolve(categoryOptions.value)
  const [courseResult, categoryResult] = await Promise.allSettled([courseRequest, categoryRequest])
  if (sequence !== requestSequence) return

  if (courseResult.status === 'rejected') {
    errorMessage.value = courseResult.reason.response?.data?.detail || 'Không thể tải danh sách khóa học. Hãy thử lại.'
  } else {
    courses.value = courseResult.value
  }

  if (categoryResult.status === 'fulfilled') {
    categoryOptions.value = categoryResult.value
    categoriesLoaded = true
    categoryError.value = ''
    const names = new Map(categoryResult.value.map((item) => [item.id, item.name]))
    courses.value = courses.value.map((course) => ({
      ...course,
      category: names.get(String(course.categoryId)) || course.category,
    }))
  } else {
    categoryError.value = categoryResult.reason.response?.data?.detail || 'Không thể tải danh mục để lọc khóa học.'
  }
  loading.value = false
}

function closeMobileFilter({ restoreFocus = false } = {}) {
  mobileFilterOpen.value = false
  if (restoreFocus) {
    nextTick(() => mobileFilterTriggerRef.value?.focus())
  }
}

function handleDocumentKeydown(event) {
  if (event.key === 'Escape' && mobileFilterOpen.value) {
    closeMobileFilter({ restoreFocus: true })
  }
}

watch(mobileFilterOpen, (isOpen) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = isOpen ? 'hidden' : ''
  if (isOpen) {
    nextTick(() => mobileFilterCloseRef.value?.focus())
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleDocumentKeydown)
  loadCatalog(true)
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  document.removeEventListener('keydown', handleDocumentKeydown)
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})

const filteredCourses = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  const filtered = courses.value.filter((course) => {
    const searchable = course.title.toLocaleLowerCase('vi')
    return (!search || searchable.includes(search))
      && (!category.value || String(course.categoryId) === category.value)
      && (!level.value || course.level === level.value)
      && (!price.value || (price.value === 'free' ? course.price === 0 : course.price > 0))
  })
  return [...filtered].sort((first, second) => {
    if (sortBy.value === 'price-asc' || sortBy.value === 'price-desc') {
      const firstHasPrice = first.price != null
      const secondHasPrice = second.price != null
      if (firstHasPrice !== secondHasPrice) return firstHasPrice ? -1 : 1
      if (firstHasPrice) return sortBy.value === 'price-asc'
        ? first.price - second.price
        : second.price - first.price
    }
    return first.title.localeCompare(second.title, 'vi')
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))
const visibleCourses = computed(() => filteredCourses.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))

const activeFilterChips = computed(() => {
  const chips = []
  if (query.value.trim()) {
    chips.push({ key: 'query', label: `Từ khóa: ${query.value.trim()}` })
  }
  if (category.value) {
    const name = categories.value.find((item) => item.id === category.value)?.name || category.value
    chips.push({ key: 'category', label: `Danh mục: ${name}` })
  }
  if (level.value) {
    chips.push({ key: 'level', label: `Trình độ: ${level.value}` })
  }
  if (price.value) {
    chips.push({ key: 'price', label: price.value === 'free' ? 'Miễn phí' : 'Có phí' })
  }
  return chips
})

function removeFilter(key) {
  if (key === 'query') {
    query.value = ''
    if (route.query.q) router.replace({ name: 'course-catalog' })
  } else if (key === 'category') {
    category.value = ''
  } else if (key === 'level') {
    level.value = ''
  } else if (key === 'price') {
    price.value = ''
  }
}

watch(() => route.query.q, (value) => { query.value = typeof value === 'string' ? value : '' })
watch(() => route.query.category_id, (value) => { category.value = typeof value === 'string' ? value : '' })
watch([query, category], () => {
  currentPage.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadCatalog(), 250)
})
watch([level, price, sortBy], () => { currentPage.value = 1 })
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function clearFilters() {
  query.value = ''
  category.value = ''
  level.value = ''
  price.value = ''
  sortBy.value = 'title'
  mobileFilterOpen.value = false
  router.replace({ name: 'course-catalog' })
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <section class="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="ui-eyebrow">Khám phá khóa học</p>
        <h1 class="ui-page-title mt-1.5">Danh sách khóa học</h1>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Tất cả khóa học đã được chuyên gia kiểm duyệt và mở đăng ký trên EduSuggest.
        </p>
      </div>

      <button
        ref="mobileFilterTriggerRef"
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-2 self-start lg:hidden"
        :aria-expanded="mobileFilterOpen"
        @click="mobileFilterOpen = true"
      >
        <SlidersHorizontal :size="15" aria-hidden="true" />
        <span>Bộ lọc</span>
        <span
          v-if="activeFilterChips.length"
          class="rounded-full bg-teal px-1.5 py-0.5 text-[11px] font-bold text-white"
        >
          {{ activeFilterChips.length }}
        </span>
      </button>
    </section>

    <!-- Category Error Alert (non-blocking) -->
    <UiAlert
      v-if="categoryError"
      variant="warning"
      :message="categoryError"
    >
      <button
        type="button"
        class="mt-2 text-xs font-semibold underline"
        @click="loadCatalog(true)"
      >
        Thử tải danh mục lại
      </button>
    </UiAlert>

    <!-- Primary Course Error State (never shows empty state when errored) -->
    <UiAlert
      v-if="errorMessage && !loading"
      variant="danger"
      title="Không thể tải danh sách khóa học"
      :message="errorMessage"
      class="max-w-2xl"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadCatalog(true)"
      >
        <RefreshCw :size="14" aria-hidden="true" />
        <span>Thử tải lại</span>
      </button>
    </UiAlert>

    <!-- Main 2-Column Layout -->
    <section v-else class="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] items-start">
      <!-- Desktop Filter Sidebar -->
      <aside class="hidden lg:block sticky top-24 bento-card bg-surface p-5 space-y-5">
        <div class="flex items-center justify-between border-b border-border pb-3">
          <div class="flex items-center gap-2 text-sm font-bold text-navy">
            <SlidersHorizontal :size="16" class="text-teal" aria-hidden="true" />
            <span>Bộ lọc khóa học</span>
          </div>
          <button
            v-if="activeFilterChips.length"
            type="button"
            class="text-xs font-semibold text-teal hover:underline"
            @click="clearFilters"
          >
            Đặt lại
          </button>
        </div>

        <div class="space-y-4">
          <label class="block text-xs font-semibold text-navy">
            Danh mục
            <select v-model="category" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Tất cả danh mục</option>
              <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>

          <label class="block text-xs font-semibold text-navy">
            Trình độ
            <select v-model="level" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Mọi trình độ</option>
              <option v-for="item in levels" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>

          <label class="block text-xs font-semibold text-navy">
            Học phí
            <select v-model="price" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Mọi mức giá</option>
              <option value="free">Miễn phí</option>
              <option value="paid">Có phí</option>
            </select>
          </label>
        </div>
      </aside>

      <!-- Right Content Area -->
      <div class="min-w-0 space-y-4">
        <!-- Search & Sort Toolbar -->
        <div class="bento-card bg-surface p-3.5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div class="relative flex-1">
            <Search :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              v-model="query"
              type="search"
              aria-label="Tìm khóa học"
              placeholder="Tìm theo tên khóa học..."
              class="ui-input pl-9 text-sm"
            >
          </div>

          <div class="flex items-center gap-2 sm:w-48">
            <label class="sr-only" for="course-sort">Sắp xếp khóa học</label>
            <select id="course-sort" v-model="sortBy" class="ui-input text-sm">
              <option value="title">Tên A → Z</option>
              <option value="price-asc">Học phí thấp → cao</option>
              <option value="price-desc">Học phí cao → thấp</option>
            </select>
          </div>
        </div>

        <!-- Active Filter Chips (removable individually) -->
        <div v-if="activeFilterChips.length" class="flex flex-wrap items-center gap-2">
          <button
            v-for="chip in activeFilterChips"
            :key="chip.key"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-xs font-semibold text-teal-dark hover:bg-teal/15 transition-colors"
            @click="removeFilter(chip.key)"
          >
            <span>{{ chip.label }}</span>
            <X :size="12" aria-hidden="true" />
          </button>

          <button
            type="button"
            class="inline-flex items-center gap-1 text-xs font-semibold text-muted hover:text-navy hover:underline ml-1"
            @click="clearFilters"
          >
            <RotateCcw :size="12" aria-hidden="true" />
            <span>Xóa tất cả</span>
          </button>
        </div>

        <!-- Results Count Bar -->
        <div v-if="!loading" class="flex items-center justify-between text-xs sm:text-sm text-muted">
          <span class="inline-flex items-center gap-1.5 font-medium text-ink">
            <BookOpen :size="15" class="text-teal" aria-hidden="true" />
            <span>{{ filteredCourses.length }} khóa học</span>
          </span>
          <span>Đã phê duyệt · Công khai</span>
        </div>

        <!-- Skeleton Loading Grid -->
        <div v-if="loading" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <UiSkeleton v-for="n in 6" :key="n" variant="card" />
        </div>

        <!-- Course Grid -->
        <template v-else-if="visibleCourses.length">
          <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <CourseCard v-for="course in visibleCourses" :key="course.id" :course="course" />
          </div>

          <div v-if="totalPages > 1" class="bento-card overflow-hidden bg-surface p-0">
            <PaginationControls
              v-model="currentPage"
              :total-pages="totalPages"
              :total-items="filteredCourses.length"
            />
          </div>
        </template>

        <!-- Empty State -->
        <UiEmptyState
          v-else
          :icon="BookOpen"
          :title="activeFilterChips.length ? 'Không tìm thấy khóa học phù hợp' : 'Chưa có khóa học công khai'"
          :description="activeFilterChips.length
            ? 'Hãy thử thay đổi từ khóa tìm kiếm hoặc bỏ bớt bộ lọc để xem thêm khóa học.'
            : 'Hiện chưa có khóa học công khai nào từ hệ thống.'"
          :action-label="activeFilterChips.length ? 'Xóa bộ lọc' : ''"
          @action="clearFilters"
        />
      </div>
    </section>

    <!-- Mobile Filter Drawer -->
    <Transition name="es-drawer">
      <div
        v-if="mobileFilterOpen"
        class="fixed inset-0 z-50 flex justify-end lg:hidden"
        role="dialog"
        aria-modal="true"
        aria-label="Bộ lọc khóa học"
      >
        <button
          type="button"
          class="fixed inset-0 bg-navy/50"
          aria-label="Đóng bộ lọc"
          @click="closeMobileFilter({ restoreFocus: true })"
        />
        <div class="es-drawer-panel relative z-10 flex h-full w-[min(88vw,340px)] flex-col bg-surface p-5 shadow-2xl">
        <div class="flex items-center justify-between border-b border-border pb-3">
          <div class="flex items-center gap-2 text-sm font-bold text-navy">
            <SlidersHorizontal :size="16" class="text-teal" aria-hidden="true" />
            <span>Bộ lọc khóa học</span>
          </div>
          <button
            ref="mobileFilterCloseRef"
            type="button"
            class="rounded-lg p-1.5 text-muted hover:bg-subtle hover:text-navy"
            aria-label="Đóng bộ lọc"
            @click="closeMobileFilter({ restoreFocus: true })"
          >
            <X :size="18" aria-hidden="true" />
          </button>
        </div>

        <div class="mt-5 flex-1 space-y-4 overflow-y-auto">
          <label class="block text-xs font-semibold text-navy">
            Danh mục
            <select v-model="category" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Tất cả danh mục</option>
              <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>

          <label class="block text-xs font-semibold text-navy">
            Trình độ
            <select v-model="level" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Mọi trình độ</option>
              <option v-for="item in levels" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>

          <label class="block text-xs font-semibold text-navy">
            Học phí
            <select v-model="price" class="ui-input mt-1.5 text-sm font-normal">
              <option value="">Mọi mức giá</option>
              <option value="free">Miễn phí</option>
              <option value="paid">Có phí</option>
            </select>
          </label>
        </div>

        <div class="mt-4 flex items-center gap-2 border-t border-border pt-4">
          <button
            type="button"
            class="ui-button ui-button--outline flex-1"
            @click="clearFilters"
          >
            Xóa lọc
          </button>
          <button
            type="button"
            class="ui-button ui-button--primary flex-1"
            @click="closeMobileFilter({ restoreFocus: true })"
          >
            Áp dụng ({{ filteredCourses.length }})
          </button>
        </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
