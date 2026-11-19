<script setup>
import { computed, ref, watch } from 'vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { REVIEW_STATUS_LABELS } from '@/constant/reviewStatus'
import { getReviewHistory } from '@/service/reviewerService'

const pageSize = 7
const query = ref('')
const typeFilter = ref('all')
const statusFilter = ref('all')
const periodFilter = ref('all')
const currentPage = ref(1)
const expandedRecordId = ref('')
const history = computed(() => getReviewHistory())

const filteredHistory = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  const now = new Date()
  const periodDays = { week: 7, month: 30 }
  const cutoff = periodFilter.value === 'all'
    ? null
    : new Date(now.getTime() - periodDays[periodFilter.value] * 24 * 60 * 60 * 1000)

  return history.value.filter((record) => {
    const matchesText = !search || `${record.title} ${record.creator} ${record.note}`.toLocaleLowerCase('vi').includes(search)
    const matchesType = typeFilter.value === 'all' || record.itemType === typeFilter.value
    const matchesStatus = statusFilter.value === 'all' || record.status === statusFilter.value
    const matchesPeriod = !cutoff || new Date(record.reviewedAt) >= cutoff

    return matchesText && matchesType && matchesStatus && matchesPeriod
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredHistory.value.length / pageSize)))
const visibleHistory = computed(() =>
  filteredHistory.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch([query, typeFilter, statusFilter, periodFilter], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

function formatDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function toggleDetails(recordId) {
  expandedRecordId.value = expandedRecordId.value === recordId ? '' : recordId
}
</script>

<template>
  <div class="space-y-5">
    <section>
      <p class="text-sm text-muted">Báo cáo</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Lịch sử kiểm duyệt</h2>
      <p class="mt-1 text-sm text-muted">Tra cứu kết quả và ghi chú của các nội dung đã xử lý.</p>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(220px,1fr)_160px_190px_160px]">
        <SearchInput v-model="query" label="Tìm lịch sử" placeholder="Tên nội dung, người tạo, ghi chú..." />
        <label class="sr-only" for="history-type">Lọc theo loại nội dung</label>
        <select id="history-type" v-model="typeFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="all">Tất cả nội dung</option>
          <option value="course">Khóa học</option>
          <option value="material">Tài liệu</option>
        </select>
        <label class="sr-only" for="history-status">Lọc theo kết quả</label>
        <select id="history-status" v-model="statusFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="all">Tất cả kết quả</option>
          <option v-for="(label, status) in REVIEW_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
        </select>
        <label class="sr-only" for="history-period">Lọc theo thời gian</label>
        <select id="history-period" v-model="periodFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="all">Mọi thời gian</option>
          <option value="week">7 ngày qua</option>
          <option value="month">30 ngày qua</option>
        </select>
      </div>

      <div v-if="visibleHistory.length" class="overflow-x-auto">
        <table class="w-full min-w-[780px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Nội dung</th>
              <th scope="col" class="px-4 py-3 font-semibold">Loại</th>
              <th scope="col" class="px-4 py-3 font-semibold">Người tạo</th>
              <th scope="col" class="px-4 py-3 font-semibold">Kết quả</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ngày xử lý</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ghi chú</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="record in visibleHistory" :key="record.id">
              <tr class="hover:bg-background/70">
                <th scope="row" class="px-4 py-4 font-semibold text-navy">{{ record.title }}</th>
                <td class="px-4 py-4 text-muted">{{ record.itemType === 'course' ? 'Khóa học' : 'Tài liệu' }}</td>
                <td class="px-4 py-4 text-muted">{{ record.creator }}</td>
                <td class="px-4 py-4"><StatusBadge :status="record.status" /></td>
                <td class="whitespace-nowrap px-4 py-4 text-muted">{{ formatDate(record.reviewedAt) }}</td>
                <td class="px-4 py-4">
                  <button
                    type="button"
                    class="font-semibold text-primary hover:underline"
                    :aria-expanded="expandedRecordId === record.id"
                    @click="toggleDetails(record.id)"
                  >
                    {{ expandedRecordId === record.id ? 'Ẩn chi tiết' : 'Xem ghi chú' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedRecordId === record.id" class="bg-background/70">
                <td colspan="6" class="px-4 py-4">
                  <div class="flex flex-wrap items-center gap-3">
                    <StatusBadge :status="record.status" />
                    <span class="text-xs text-muted">Xử lý ngày {{ formatDate(record.reviewedAt) }}</span>
                  </div>
                  <p class="mt-2 text-sm leading-6 text-muted">{{ record.note }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="Không có lịch sử phù hợp" description="Thử thay đổi từ khóa hoặc các bộ lọc thời gian, loại nội dung và kết quả." />

      <PaginationControls
        v-if="filteredHistory.length"
        v-model="currentPage"
        :total-pages="totalPages"
        :total-items="filteredHistory.length"
      />
    </section>
  </div>
</template>
