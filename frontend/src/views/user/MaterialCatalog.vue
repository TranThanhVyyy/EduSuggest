<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, Filter, RefreshCw, RotateCcw, Search, X } from 'lucide-vue-next'
import MaterialCard from '@/components/user/MaterialCard.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import { fetchPublicMaterials, fetchUserCategories } from '@/service/userApiService'

const route = useRoute()
const router = useRouter()
const materials = ref([])
const categories = ref([])
const loading = ref(true)
const error = ref('')

const searchQuery = ref(typeof route.query.q === 'string' ? route.query.q : '')
const selectedCategory = ref(typeof route.query.category_id === 'string' ? route.query.category_id : '')
const selectedType = ref('')
const currentPage = ref(1)
const pageSize = 12
const totalItems = ref(0)
const totalPages = ref(0)
let searchTimer = null

const materialTypes = ['Tất cả', 'DOCUMENT', 'PDF', 'SLIDE', 'CODE', 'EXERCISE', 'REFERENCE']

async function loadMaterials() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchPublicMaterials({
      query: searchQuery.value,
      categoryId: selectedCategory.value || undefined,
      materialType: selectedType.value || undefined,
      page: currentPage.value,
      pageSize,
    })
    if (result.totalPages > 0 && currentPage.value > result.totalPages) {
      currentPage.value = result.totalPages
      return
    }
    materials.value = result.items
    totalItems.value = result.total
    totalPages.value = result.totalPages
  } catch (cause) {
    error.value = cause?.response?.data?.detail || cause?.message || 'Không thể tải danh mục tài liệu.'
    materials.value = []
    totalItems.value = 0
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

async function loadData() {
  const [, catResult] = await Promise.allSettled([
    loadMaterials(),
    fetchUserCategories(),
  ])
  if (catResult.status === 'fulfilled') {
    categories.value = catResult.value
  }
}

watch(() => route.query.q, (value) => {
  searchQuery.value = typeof value === 'string' ? value : ''
})

watch(() => route.query.category_id, (value) => {
  selectedCategory.value = typeof value === 'string' ? value : ''
})

const activeFilterChips = computed(() => {
  const chips = []
  if (searchQuery.value.trim()) {
    chips.push({ key: 'query', label: `Từ khóa: ${searchQuery.value.trim()}` })
  }
  if (selectedCategory.value) {
    const name = categories.value.find((cat) => String(cat.id) === String(selectedCategory.value))?.name
      || `Danh mục #${selectedCategory.value}`
    chips.push({ key: 'category', label: `Danh mục: ${name}` })
  }
  if (selectedType.value) {
    chips.push({ key: 'type', label: `Định dạng: ${selectedType.value}` })
  }
  return chips
})

function removeFilter(key) {
  if (key === 'query') {
    searchQuery.value = ''
    if (route.query.q) {
      const nextQuery = { ...route.query }
      delete nextQuery.q
      router.replace({ name: 'material-catalog', query: nextQuery })
    }
  } else if (key === 'category') {
    selectedCategory.value = ''
    if (route.query.category_id) {
      const nextQuery = { ...route.query }
      delete nextQuery.category_id
      router.replace({ name: 'material-catalog', query: nextQuery })
    }
  } else if (key === 'type') {
    selectedType.value = ''
  }
}

watch([selectedCategory, selectedType], () => {
  if (currentPage.value !== 1) {
    currentPage.value = 1
  } else {
    loadMaterials()
  }
})

watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (currentPage.value !== 1) {
      currentPage.value = 1
    } else {
      loadMaterials()
    }
  }, 250)
})

watch(currentPage, () => {
  loadMaterials()
})

onMounted(loadData)

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

function resetFilters() {
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedType.value = ''
  currentPage.value = 1
  if (route.query.q || route.query.category_id) {
    router.replace({ name: 'material-catalog' })
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header Hero Section -->
    <section class="border-b border-border pb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p class="ui-eyebrow">Thư viện mở EduSuggest</p>
          <h1 class="ui-page-title mt-2">Tài liệu học tập chuyên khảo</h1>
          <p class="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            Khám phá tài liệu độc lập và học liệu chuyên sâu được kiểm duyệt bởi các chuyên gia học thuật.
          </p>
        </div>
        <button
          type="button"
          class="ui-button ui-button--secondary inline-flex items-center gap-2 self-start text-xs"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </section>

    <!-- Error Alert -->
    <UiAlert
      v-if="error"
      variant="danger"
      :message="error"
      dismissible
      @dismiss="error = ''"
    />

    <!-- Filter Bento Toolbar -->
    <div class="bento-card p-4 bg-surface space-y-3">
      <div class="flex flex-col sm:flex-row gap-3">
        <!-- Search -->
        <div class="relative flex-1">
          <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            aria-label="Tìm kiếm tài liệu học tập"
            placeholder="Tìm theo tiêu đề, chủ đề tài liệu..."
            class="ui-input pl-9 text-xs sm:text-sm"
          >
        </div>

        <!-- Category Dropdown -->
        <div class="w-full sm:w-56">
          <select
            v-model="selectedCategory"
            aria-label="Lọc theo danh mục tài liệu"
            class="ui-input text-xs sm:text-sm"
          >
            <option value="">Tất cả danh mục</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Format Type Filter Chips -->
      <div class="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3 text-xs">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="mr-1 flex items-center gap-1 font-semibold text-navy">
            <Filter :size="13" class="text-teal" aria-hidden="true" /> Định dạng:
          </span>
          <button
            v-for="t in materialTypes"
            :key="t"
            type="button"
            :aria-pressed="selectedType === t || (!selectedType && t === 'Tất cả')"
            :class="[
              'rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors duration-150 active:scale-[0.97]',
              (selectedType === t || (!selectedType && t === 'Tất cả'))
                ? 'border-teal bg-teal text-white shadow-sm'
                : 'border-border bg-subtle text-ink hover:border-teal/40 hover:text-navy'
            ]"
            @click="selectedType = t === 'Tất cả' ? '' : t"
          >
            {{ t }}
          </button>
        </div>

        <span class="inline-flex items-center gap-1.5 font-medium text-ink">
          <FileText :size="14" class="text-teal" aria-hidden="true" />
          <span>Hiển thị {{ materials.length }} / {{ totalItems }} tài liệu</span>
        </span>
      </div>
    </div>

    <!-- Active Filter Chips (Consistent with CourseCatalog.vue) -->
    <div v-if="activeFilterChips.length" class="flex flex-wrap items-center gap-2">
      <button
        v-for="chip in activeFilterChips"
        :key="chip.key"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-xs font-semibold text-teal-dark transition-colors duration-150 hover:bg-teal/15"
        @click="removeFilter(chip.key)"
      >
        <span>{{ chip.label }}</span>
        <X :size="12" aria-hidden="true" />
      </button>

      <button
        type="button"
        class="ml-1 inline-flex items-center gap-1 text-xs font-semibold text-muted hover:text-navy hover:underline"
        @click="resetFilters"
      >
        <RotateCcw :size="12" aria-hidden="true" />
        <span>Xóa tất cả</span>
      </button>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <UiSkeleton v-for="n in 8" :key="n" variant="card" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!materials.length" class="bento-card p-8 bg-surface">
      <UiEmptyState
        title="Không tìm thấy tài liệu phù hợp"
        description="Hãy thử thay đổi từ khóa tìm kiếm hoặc bỏ bộ lọc định dạng để khám phá thêm nhiều tài liệu."
        action-label="Xóa bộ lọc"
        @action="resetFilters"
      />
    </div>

    <!-- Material Bento Grid -->
    <template v-else>
      <section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MaterialCard
          v-for="mat in materials"
          :key="mat.id"
          :material="mat"
        />
      </section>

      <div v-if="totalPages > 1" class="bento-card p-0 bg-surface overflow-hidden">
        <PaginationControls
          v-model="currentPage"
          :total-pages="totalPages"
          :total-items="totalItems"
        />
      </div>
    </template>
  </div>
</template>
