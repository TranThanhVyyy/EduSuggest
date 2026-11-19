<script setup>
import { computed, ref, watch } from 'vue'
import { Eye, FileText } from 'lucide-vue-next'
import { REVIEW_STATUS_LABELS } from '@/constant/reviewStatus'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getReviewItems } from '@/service/reviewerService'

const props = defineProps({
  kind: { type: String, required: true },
})

const pageSize = 5
const query = ref('')
const statusFilter = ref('all')
const categoryFilter = ref('all')
const currentPage = ref(1)
const items = computed(() => getReviewItems(props.kind))
const isCourse = computed(() => props.kind === 'course')
const title = computed(() => (isCourse.value ? 'Khóa học chờ duyệt' : 'Tài liệu chờ duyệt'))
const categoryLabel = computed(() => (isCourse.value ? 'Danh mục' : 'Loại tài liệu'))
const categories = computed(() => [
  ...new Set(items.value.map((item) => (isCourse.value ? item.category : item.documentType))),
])

const filteredItems = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')

  return items.value.filter((item) => {
    const category = isCourse.value ? item.category : item.documentType
    const matchesText =
      !search ||
      `${item.title} ${item.creator} ${category}`.toLocaleLowerCase('vi').includes(search)
    const matchesStatus = statusFilter.value === 'all' || item.status === statusFilter.value
    const matchesCategory = categoryFilter.value === 'all' || category === categoryFilter.value

    return matchesText && matchesStatus && matchesCategory
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize)))
const visibleItems = computed(() =>
  filteredItems.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch([query, statusFilter, categoryFilter], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

function detailRoute(item) {
  return isCourse.value
    ? { name: 'reviewer-course-detail', params: { id: item.id } }
    : { name: 'reviewer-material-detail', params: { id: item.id } }
}

function submittedDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(new Date(value))
}
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Quản lý kiểm duyệt</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ title }}</h2>
        <p class="mt-1 text-sm text-muted">Tìm kiếm, lọc và mở nội dung để xem xét chi tiết.</p>
      </div>
      <span class="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">{{ filteredItems.length }} nội dung</span>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(220px,1fr)_190px_210px]">
        <SearchInput v-model="query" :label="`Tìm ${isCourse ? 'khóa học' : 'tài liệu'}`" :placeholder="`Tìm theo tên ${isCourse ? 'khóa học' : 'tài liệu'} hoặc người tạo...`" />
        <label class="sr-only" for="review-status-filter">Lọc theo trạng thái</label>
        <select id="review-status-filter" v-model="statusFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="all">Tất cả trạng thái</option>
          <option v-for="(label, status) in REVIEW_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
        </select>
        <label class="sr-only" for="review-category-filter">Lọc theo {{ categoryLabel.toLocaleLowerCase('vi') }}</label>
        <select id="review-category-filter" v-model="categoryFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="all">Tất cả {{ categoryLabel.toLocaleLowerCase('vi') }}</option>
          <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
        </select>
      </div>

      <div v-if="visibleItems.length" class="overflow-x-auto">
        <table class="w-full min-w-[790px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">STT</th>
              <th scope="col" class="px-4 py-3 font-semibold">Tên nội dung</th>
              <th scope="col" class="px-4 py-3 font-semibold">{{ categoryLabel }}</th>
              <th scope="col" class="px-4 py-3 font-semibold">Người tạo</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ngày gửi</th>
              <th scope="col" class="px-4 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="px-4 py-3 font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="(item, index) in visibleItems" :key="item.id" class="transition hover:bg-background/70">
              <td class="px-4 py-4 text-muted">{{ (currentPage - 1) * pageSize + index + 1 }}</td>
              <th scope="row" class="max-w-64 px-4 py-4 font-semibold text-navy">
                <span class="block truncate">{{ item.title }}</span>
                <span class="mt-1 block truncate text-xs font-normal text-muted">{{ item.creatorEmail }}</span>
              </th>
              <td class="px-4 py-4 text-muted">{{ isCourse ? item.category : item.documentType }}</td>
              <td class="px-4 py-4 text-muted">{{ item.creator }}</td>
              <td class="whitespace-nowrap px-4 py-4 text-muted">{{ submittedDate(item.submittedAt) }}</td>
              <td class="px-4 py-4"><StatusBadge :status="item.status" /></td>
              <td class="px-4 py-4">
                <RouterLink :to="detailRoute(item)" class="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-primary transition hover:bg-primary/5 focus-visible:outline-2 focus-visible:outline-primary">
                  <Eye :size="15" aria-hidden="true" /> Xem chi tiết
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        :title="items.length ? 'Không tìm thấy kết quả' : `Chưa có ${isCourse ? 'khóa học' : 'tài liệu'} cần duyệt`"
        :description="items.length ? 'Hãy thay đổi từ khóa tìm kiếm hoặc bộ lọc.' : 'Nội dung mới gửi sẽ xuất hiện tại đây.'"
      />

      <PaginationControls
        v-if="filteredItems.length"
        v-model="currentPage"
        :total-pages="totalPages"
        :total-items="filteredItems.length"
      />
    </section>

    <p class="flex items-center gap-2 text-xs text-muted">
      <FileText :size="15" aria-hidden="true" />
      Các thao tác cập nhật dữ liệu mẫu trong phiên hiện tại.
    </p>
  </div>
</template>
