<script setup>
import { computed, ref, watch } from 'vue'
import { BookOpen, RotateCcw, SlidersHorizontal } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import CourseCard from '@/components/user/CourseCard.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import { getPublicCourses } from '@/service/userService'

const route = useRoute()
const router = useRouter()
const pageSize = 6
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const category = ref('')
const level = ref('')
const price = ref('')
const sortBy = ref('title')
const currentPage = ref(1)
const courses = computed(() => getPublicCourses())
const categories = computed(() => [...new Set(courses.value.map((course) => course.category))].sort())
const levels = computed(() => [...new Set(courses.value.map((course) => course.level))].sort())

const filteredCourses = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  const filtered = courses.value.filter((course) => {
    const searchable = `${course.title} ${course.description} ${course.provider} ${course.category} ${course.keywords.join(' ')}`.toLocaleLowerCase('vi')
    return (!search || searchable.includes(search))
      && (!category.value || course.category === category.value)
      && (!level.value || course.level === level.value)
      && (!price.value || (price.value === 'free' ? course.price === 0 : course.price > 0))
  })
  return [...filtered].sort((first, second) => {
    if (sortBy.value === 'price-asc') return first.price - second.price
    if (sortBy.value === 'price-desc') return second.price - first.price
    return first.title.localeCompare(second.title, 'vi')
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))
const visibleCourses = computed(() => filteredCourses.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))
const activeFilters = computed(() => [
  query.value && `Từ khóa: ${query.value}`,
  category.value && `Danh mục: ${category.value}`,
  level.value && `Trình độ: ${level.value}`,
  price.value && (price.value === 'free' ? 'Miễn phí' : 'Có phí'),
].filter(Boolean))

watch(() => route.query.q, (value) => { query.value = typeof value === 'string' ? value : '' })
watch([query, category, level, price, sortBy], () => { currentPage.value = 1 })
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
    <section class="rounded-2xl bg-primary p-6 text-white sm:p-8">
      <p class="text-sm font-semibold text-white/75">Khám phá</p>
      <h1 class="mt-1 text-3xl font-bold">Danh sách khóa học</h1>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-white/85">Tìm nội dung công khai trong dữ liệu mẫu EduSuggest. Khóa học chưa được phê duyệt sẽ không xuất hiện tại đây.</p>
    </section>

    <section class="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside class="h-fit rounded-2xl border border-slate-200 bg-white p-4">
        <div class="flex items-center gap-2 font-bold text-navy"><SlidersHorizontal :size="17" aria-hidden="true" /> Bộ lọc</div>
        <div class="mt-4 space-y-4">
          <label class="block text-xs font-semibold text-muted">Danh mục
            <select v-model="category" class="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary">
              <option value="">Tất cả danh mục</option><option v-for="item in categories" :key="item">{{ item }}</option>
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
          <SearchInput v-model="query" label="Tìm khóa học" placeholder="Tên, mô tả hoặc từ khóa..."/>
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
  </div>
</template>
