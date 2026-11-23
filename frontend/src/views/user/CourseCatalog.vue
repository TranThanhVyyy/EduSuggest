<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { BookOpen, RotateCcw, SlidersHorizontal } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import { fetchUserCategories, fetchUserCourses } from '@/service/userApiService'

const route = useRoute()
const router = useRouter()
const pageSize = 6
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const category = ref('')
const level = ref('')
const price = ref('')
const sortBy = ref('title')
const currentPage = ref(1)
const courses = ref([])
const categoryOptions = ref([])
let categoriesLoaded = false
const loading = ref(true)
const errorMessage = ref('')
const categoryError = ref('')
const categories = computed(() => categoryOptions.value)
const levels = computed(() => [...new Set(courses.value.map((course) => course.level))].sort())
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
onMounted(() => loadCatalog(true))

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
const activeFilters = computed(() => [
  query.value && `Từ khóa: ${query.value}`,
  category.value && `Danh mục: ${categories.value.find((item) => item.id === category.value)?.name || category.value}`,
  level.value && `Trình độ: ${level.value}`,
  price.value && (price.value === 'free' ? 'Miễn phí' : 'Có phí'),
].filter(Boolean))

watch(() => route.query.q, (value) => { query.value = typeof value === 'string' ? value : '' })
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
  router.replace({ name: 'course-catalog' })
}
</script>

<template>
  <div class="space-y-6">
    <section class="border-b border-border pb-5">
      <p class="ui-eyebrow">Khám phá</p>
      <h1 class="ui-page-title mt-2">Danh sách khóa học</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-muted">Danh mục hiển thị khóa học đã được phê duyệt và công khai.</p>
    </section>

    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải khóa học…</p>
    <section v-else-if="errorMessage" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert"><p class="text-sm text-danger">{{ errorMessage }}</p><button class="mt-3 text-sm font-medium text-secondary underline" @click="loadCatalog">Thử tải lại</button></section>
    <section v-else-if="courses.length" class="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
      <p v-if="categoryError" class="text-sm text-danger lg:col-span-2" role="alert">{{ categoryError }} <button type="button" class="font-medium underline" @click="loadCatalog(true)">Thử tải danh mục lại</button></p>
      <aside class="h-fit rounded-2xl border border-slate-200 bg-white p-4">
        <div class="flex items-center gap-2 font-bold text-navy"><SlidersHorizontal :size="17" aria-hidden="true" /> Bộ lọc</div>
        <div class="mt-4 space-y-4">
          <label class="block text-xs font-semibold text-muted">Danh mục
            <select v-model="category" class="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary">
              <option value="">Tất cả danh mục</option><option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>
          <label class="block text-xs font-semibold text-muted">Trình độ
            <select v-model="level" class="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary">
              <option value="">Mọi trình độ</option><option v-for="item in levels" :key="item">{{ item }}</option>
            </select>
          </label>
          <label class="block text-xs font-semibold text-muted">Học phí
            <select v-model="price" class="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary">
              <option value="">Mọi mức giá</option><option value="free">Miễn phí</option><option value="paid">Có phí</option>
            </select>
          </label>
          <button type="button" class="inline-flex items-center gap-2 text-xs font-semibold text-primary hover:underline" @click="clearFilters"><RotateCcw :size="14" aria-hidden="true" /> Xóa bộ lọc</button>
        </div>
      </aside>

      <div class="min-w-0">
        <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_190px]">
          <SearchInput v-model="query" label="Tìm khóa học" placeholder="Tên khóa học..."/>
          <label class="sr-only" for="course-sort">Sắp xếp khóa học</label>
          <select id="course-sort" v-model="sortBy" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary">
            <option value="title">Tên khóa học</option><option value="price-asc">Giá thấp đến cao</option><option value="price-desc">Giá cao đến thấp</option>
          </select>
        </div>
        <div v-if="activeFilters.length" class="mt-3 flex flex-wrap items-center gap-2">
          <span v-for="filter in activeFilters" :key="filter" class="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{{ filter }}</span>
          <button type="button" class="text-xs font-semibold text-muted hover:text-primary" @click="clearFilters">Xóa tất cả</button>
        </div>
        <div class="mt-4 flex items-center justify-between text-sm text-muted"><span class="inline-flex items-center gap-2"><BookOpen :size="16" aria-hidden="true" />{{ filteredCourses.length }} khóa học</span><span>Đã phê duyệt · công khai</span></div>
        <div v-if="visibleCourses.length" class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <CourseCard v-for="course in visibleCourses" :key="course.id" :course="course" />
        </div>
        <div v-else class="mt-4 rounded-2xl border border-slate-200 bg-white">
          <EmptyState title="Không tìm thấy khóa học" description="Thay đổi từ khóa tìm kiếm hoặc xóa một số bộ lọc." />
        </div>
        <PaginationControls v-if="filteredCourses.length" v-model="currentPage" class="mt-4 rounded-xl border border-slate-200 bg-white" :total-pages="totalPages" :total-items="filteredCourses.length" />
      </div>
    </section>
    <section v-else-if="!loading" class="max-w-2xl border-y border-border py-3" aria-live="polite">
      <EmptyState title="Chưa có khóa học công khai" description="Danh mục khóa học chưa nhận được dữ liệu từ Backend." />
    </section>
  </div>
</template>
