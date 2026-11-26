<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  BookOpen,
  FileText,
  Filter,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  fetchRecommendedCourses,
  fetchRecommendedMaterialsWithMeta,
  fetchUserCategories,
} from '@/service/userApiService'

const route = useRoute()
const router = useRouter()
const isMaterialView = computed(() => route.name === 'material-recommendations')

const rawItems = ref([])
const categories = ref([])
const loading = ref(true)
const error = ref('')
const isForbidden = ref(false)
const strategy = ref('none')
const personalized = ref(false)
const hasMaterialEnrollments = ref(true)
const failedMaterialCourseCount = ref(0)

// Interactive Filter states
const selectedCategory = ref('')
const selectedLevel = ref('')
const selectedMaterialType = ref('')
const searchQuery = ref('')

const levels = ['Tất cả', 'Cơ bản', 'Trung cấp', 'Nâng cao']
const defaultMaterialTypes = ['Tất cả', 'DOCUMENT', 'PDF', 'SLIDE', 'CODE', 'EXERCISE', 'REFERENCE']

const materialTypes = computed(() => {
  const dynamicTypes = new Set(
    rawItems.value
      .map((item) => String(item.type || '').trim().toUpperCase())
      .filter(Boolean),
  )
  const merged = new Set(['Tất cả', ...defaultMaterialTypes.slice(1), ...dynamicTypes])
  return Array.from(merged)
})

const categoryNameMap = computed(() => new Map(categories.value.map((c) => [String(c.id), c.name])))

function switchTab(targetRouteName) {
  if (route.name === targetRouteName) return
  clearFilters()
  router.push({ name: targetRouteName })
}

async function loadData() {
  loading.value = true
  error.value = ''
  isForbidden.value = false
  strategy.value = 'none'
  personalized.value = false
  hasMaterialEnrollments.value = true
  failedMaterialCourseCount.value = 0

  try {
    if (isMaterialView.value) {
      const courseId = route.query.course_id ? Number(route.query.course_id) : null
      const lessonId = route.query.lesson_id != null ? Number(route.query.lesson_id) : null
      const [matResult, catResult] = await Promise.allSettled([
        fetchRecommendedMaterialsWithMeta(courseId, { lessonId, limit: 12 }),
        fetchUserCategories(),
      ])
      if (catResult.status === 'fulfilled') {
        categories.value = catResult.value
      }
      if (matResult.status === 'fulfilled') {
        const names = new Map((catResult.status === 'fulfilled' ? catResult.value : categories.value).map((c) => [String(c.id), c.name]))
        rawItems.value = (matResult.value.items || []).map((item) => ({
          ...item,
          categoryName: names.get(String(item.categoryId)) || '',
        }))
        strategy.value = matResult.value.strategy || 'none'
        personalized.value = Boolean(matResult.value.personalized)
        hasMaterialEnrollments.value = courseId != null || Boolean(matResult.value.hasEnrollments)
        failedMaterialCourseCount.value = Number(matResult.value.failedCourseCount || 0)
      } else {
        throw matResult.reason
      }
    } else {
      const [recResult, catResult] = await Promise.allSettled([
        fetchRecommendedCourses({ limit: 18 }),
        fetchUserCategories(),
      ])
      if (catResult.status === 'fulfilled') {
        categories.value = catResult.value
      }
      if (recResult.status === 'fulfilled') {
        const names = new Map((catResult.status === 'fulfilled' ? catResult.value : categories.value).map((c) => [String(c.id), c.name]))
        rawItems.value = (recResult.value.items || []).map((item) => ({
          ...item,
          category: names.get(String(item.categoryId)) || item.category,
        }))
        strategy.value = recResult.value.strategy || 'none'
        personalized.value = Boolean(recResult.value.personalized)
      } else {
        throw recResult.reason
      }
    }
  } catch (cause) {
    rawItems.value = []
    if (cause.response?.status === 403) {
      isForbidden.value = true
      error.value = cause.response?.data?.detail || 'Bạn cần đăng ký khóa học trước khi xem tài liệu gợi ý theo khóa học này.'
    } else {
      error.value = cause.response?.data?.detail || 'Không thể tải danh sách gợi ý. Vui lòng thử lại.'
    }
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  return rawItems.value.filter((item) => {
    if (selectedCategory.value) {
      const matchCatId = String(item.categoryId) === String(selectedCategory.value)
      const catLabel = item.categoryName || item.category || categoryNameMap.value.get(String(item.categoryId)) || ''
      const matchCatName = catLabel.toLowerCase() === selectedCategory.value.toLowerCase()
      if (!matchCatId && !matchCatName) return false
    }

    if (!isMaterialView.value && selectedLevel.value && selectedLevel.value !== 'Tất cả') {
      if (item.level !== selectedLevel.value) return false
    }

    if (isMaterialView.value && selectedMaterialType.value && selectedMaterialType.value !== 'Tất cả') {
      if (String(item.type || '').toUpperCase() !== selectedMaterialType.value.toUpperCase()) return false
    }

    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase()
      const inTitle = item.title?.toLowerCase().includes(q)
      const inDesc = item.description?.toLowerCase().includes(q)
      if (!inTitle && !inDesc) return false
    }

    return true
  })
})

const hasActiveFilters = computed(() => {
  return Boolean(
    selectedCategory.value
    || (!isMaterialView.value && selectedLevel.value && selectedLevel.value !== 'Tất cả')
    || (isMaterialView.value && selectedMaterialType.value && selectedMaterialType.value !== 'Tất cả')
    || searchQuery.value.trim(),
  )
})

function clearFilters() {
  selectedCategory.value = ''
  selectedLevel.value = ''
  selectedMaterialType.value = ''
  searchQuery.value = ''
}

watch(() => route.fullPath, loadData)
onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <!-- 1. HEADER + HUB TABS -->
    <header class="space-y-5 border-b border-border pb-6">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span class="ui-tag-label">
            <Sparkles :size="15" aria-hidden="true" />
            <span>Trung tâm gợi ý EduSuggest</span>
          </span>
          <h1 class="ui-page-title mt-1.5">
            {{ isMaterialView ? 'Gợi ý tài liệu học tập' : 'Gợi ý khóa học' }}
          </h1>
          <p class="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            {{ isMaterialView
              ? 'Tài liệu học tập được gợi ý độc lập hoặc theo ngữ cảnh khóa học/bài học bằng TF-IDF & Cosine Similarity.'
              : 'Khóa học được đề xuất riêng biệt dựa trên dữ liệu khóa học và lịch sử học tập bằng TF-IDF & Cosine Similarity.'
            }}
          </p>
        </div>

        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>

      <!-- Independent Stream Tabs -->
      <nav aria-label="Chuyển luồng gợi ý" class="flex flex-wrap items-center gap-2" role="tablist">
        <button
          type="button"
          role="tab"
          :aria-selected="!isMaterialView"
          :class="[
            'inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-colors',
            !isMaterialView
              ? 'border-navy bg-navy text-white'
              : 'border-border bg-surface text-ink hover:border-teal/40 hover:text-teal',
          ]"
          @click="switchTab('course-recommendations')"
        >
          <BookOpen :size="15" aria-hidden="true" />
          <span>Khóa học</span>
        </button>

        <button
          type="button"
          role="tab"
          :aria-selected="isMaterialView"
          :class="[
            'inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-colors',
            isMaterialView
              ? 'border-navy bg-navy text-white'
              : 'border-border bg-surface text-ink hover:border-teal/40 hover:text-teal',
          ]"
          @click="switchTab('material-recommendations')"
        >
          <FileText :size="15" aria-hidden="true" />
          <span>Tài liệu học tập</span>
        </button>
      </nav>

      <!-- Cold-start notice (ONLY when API returns strategy === 'latest') -->
      <UiAlert
        v-if="!loading && !error && strategy === 'latest'"
        variant="info"
        title="Chế độ khám phá mới cập nhật"
        :message="isMaterialView
          ? 'Đang hiển thị tài liệu mới cập nhật. Hãy tiếp tục học để cá nhân hóa gợi ý.'
          : 'Đang hiển thị nội dung mới cập nhật. Hãy tiếp tục học để cá nhân hóa gợi ý.'
        "
      />
    </header>

    <!-- 2. INTERACTIVE FILTER CONTROLS (Both Courses and Materials) -->
    <section
      v-if="!error"
      aria-label="Bộ lọc gợi ý"
      class="bento-card space-y-4 bg-surface p-4"
    >
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="relative flex-1 max-w-md">
          <Search :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            :placeholder="isMaterialView ? 'Tìm theo tên hoặc mô tả tài liệu...' : 'Tìm theo tên khóa học hoặc kỹ năng...'"
            class="ui-input pl-9 text-sm"
          >
        </div>

        <!-- Course Level Filter -->
        <div v-if="!isMaterialView" class="flex flex-wrap items-center gap-1.5 text-xs">
          <span class="mr-1 flex items-center gap-1 font-semibold text-muted">
            <Filter :size="13" aria-hidden="true" />
            <span>Trình độ:</span>
          </span>
          <button
            v-for="lvl in levels"
            :key="lvl"
            type="button"
            :class="[
              'rounded-md px-2.5 py-1 font-medium transition-colors',
              (selectedLevel === lvl || (!selectedLevel && lvl === 'Tất cả'))
                ? 'bg-navy text-white'
                : 'bg-subtle text-ink hover:bg-border',
            ]"
            @click="selectedLevel = (lvl === 'Tất cả' ? '' : lvl)"
          >
            {{ lvl }}
          </button>
        </div>

        <!-- Material Type Filter -->
        <div v-else class="flex flex-wrap items-center gap-1.5 text-xs">
          <span class="mr-1 flex items-center gap-1 font-semibold text-muted">
            <Filter :size="13" aria-hidden="true" />
            <span>Loại tài liệu:</span>
          </span>
          <button
            v-for="mType in materialTypes"
            :key="mType"
            type="button"
            :class="[
              'rounded-md px-2.5 py-1 font-medium transition-colors',
              (selectedMaterialType === mType || (!selectedMaterialType && mType === 'Tất cả'))
                ? 'bg-navy text-white'
                : 'bg-subtle text-ink hover:bg-border',
            ]"
            @click="selectedMaterialType = (mType === 'Tất cả' ? '' : mType)"
          >
            {{ mType }}
          </button>
        </div>
      </div>

      <!-- Category Pills -->
      <div v-if="!isMaterialView && categories.length" class="flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-3">
        <span class="mr-1 text-xs font-semibold text-muted">Danh mục:</span>
        <button
          type="button"
          :class="[
            'rounded-full px-3 py-0.5 text-xs font-medium transition-colors',
            !selectedCategory ? 'bg-teal text-white' : 'bg-subtle text-ink hover:bg-border',
          ]"
          @click="selectedCategory = ''"
        >
          Tất cả
        </button>
        <button
          v-for="cat in categories"
          :key="cat.id"
          type="button"
          :class="[
            'rounded-full px-3 py-0.5 text-xs font-medium transition-colors',
            selectedCategory === cat.id ? 'bg-teal text-white' : 'bg-subtle text-ink hover:bg-border',
          ]"
          @click="selectedCategory = selectedCategory === cat.id ? '' : cat.id"
        >
          {{ cat.name }}
        </button>
      </div>

      <div v-if="hasActiveFilters" class="flex items-center justify-between pt-1 text-xs text-muted">
        <span>Đang lọc theo tiêu chí đã chọn ({{ filteredItems.length }} kết quả)</span>
        <button
          type="button"
          class="inline-flex items-center gap-1 font-semibold text-teal hover:underline"
          @click="clearFilters"
        >
          <X :size="13" aria-hidden="true" />
          <span>Xóa bộ lọc</span>
        </button>
      </div>
    </section>

    <!-- 3. CONTENT LISTING -->
    <main aria-label="Danh sách gợi ý">
      <UiAlert
        v-if="isMaterialView && !loading && !error && failedMaterialCourseCount"
        variant="warning"
        title="Một số khóa học chưa tải được tài liệu gợi ý"
        :message="`Đã bỏ qua ${failedMaterialCourseCount} khóa học bị lỗi; kết quả còn lại vẫn được hiển thị.`"
        class="mb-4 max-w-2xl"
      />
      <!-- Loading State -->
      <div v-if="loading" class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <UiSkeleton v-for="i in 6" :key="i" variant="card" />
      </div>

      <!-- Error / 403 State -->
      <UiAlert
        v-else-if="error"
        :variant="isForbidden ? 'warning' : 'danger'"
        :title="isForbidden ? 'Chưa có quyền truy cập gợi ý theo khóa học' : 'Không thể tải gợi ý'"
        :message="error"
        class="max-w-2xl"
      >
        <div class="mt-3 flex flex-wrap items-center gap-2">
          <button
            v-if="!isForbidden"
            type="button"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
            @click="loadData"
          >
            <RefreshCw :size="14" aria-hidden="true" />
            <span>Thử lại</span>
          </button>
          <RouterLink
            v-if="isForbidden && route.query.course_id"
            :to="{ name: 'course-detail', params: { id: String(route.query.course_id) } }"
            class="ui-button ui-button--primary ui-button--sm"
          >
            Xem chi tiết khóa học để đăng ký
          </RouterLink>
        </div>
      </UiAlert>

      <!-- Results Grid -->
      <div
        v-else-if="filteredItems.length"
        class="grid gap-5 md:grid-cols-2 xl:grid-cols-3"
      >
        <template v-if="isMaterialView">
          <MaterialCard
            v-for="item in filteredItems"
            :key="item.id"
            :material="item"
          />
        </template>
        <template v-else>
          <CourseCard
            v-for="item in filteredItems"
            :key="item.id"
            :course="item"
          />
        </template>
      </div>

      <!-- Empty State -->
      <UiEmptyState
        v-else
        :icon="isMaterialView ? FileText : BookOpen"
        :title="isMaterialView
          ? (!hasMaterialEnrollments ? 'Đăng ký khóa học để nhận gợi ý tài liệu' : 'Chưa có gợi ý tài liệu phù hợp')
          : 'Không tìm thấy khóa học phù hợp'"
        :description="hasActiveFilters
          ? 'Không có kết quả nào khớp với các bộ lọc bạn đã chọn. Hãy thử xóa hoặc điều chỉnh bộ lọc.'
          : (isMaterialView
            ? (!hasMaterialEnrollments
              ? 'Tài liệu đề xuất chỉ được lấy từ các khóa học bạn đã đăng ký.'
              : 'Hiện chưa có tài liệu phù hợp trong các khóa học bạn đã đăng ký.')
            : 'Hiện tại hệ thống chưa có dữ liệu gợi ý khóa học phù hợp.')
        "
        :action-label="hasActiveFilters ? 'Xóa bộ lọc' : (isMaterialView ? 'Xem thư viện tài liệu' : 'Khám phá tất cả khóa học')"
        :action-route="hasActiveFilters ? null : { name: isMaterialView ? 'material-catalog' : 'course-catalog' }"
        @action="clearFilters"
      />
    </main>
  </div>
</template>
