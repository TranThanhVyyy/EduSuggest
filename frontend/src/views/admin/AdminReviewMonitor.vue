<script setup>
import { computed, ref, watch } from 'vue'
import { FileSearch } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import { REVIEW_STATUS, REVIEW_STATUS_LABELS } from '@/constant/reviewStatus'
import { getAdminReviewMonitor } from '@/service/adminService'

const pageSize = 8
const query = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const reviewerFilter = ref('')
const currentPage = ref(1)
const expandedId = ref('')
const records = computed(() => getAdminReviewMonitor())
const reviewers = computed(() => [...new Set(records.value.map((record) => record.reviewerName).filter((name) => name && name !== 'Chưa có dữ liệu'))])

const filteredRecords = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return records.value.filter((record) => {
    const text = `${record.id} ${record.title} ${record.creator} ${record.reviewerName} ${record.note}`.toLocaleLowerCase('vi')
    return (!search || text.includes(search))
      && (!typeFilter.value || record.itemType === typeFilter.value)
      && (!statusFilter.value || record.status === statusFilter.value)
      && (!reviewerFilter.value || record.reviewerName === reviewerFilter.value)
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRecords.value.length / pageSize)))
const visibleRecords = computed(() => filteredRecords.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))
const statusCounts = computed(() => Object.values(REVIEW_STATUS).map((status) => ({
  status,
  count: records.value.filter((record) => record.status === status).length,
})))

watch([query, typeFilter, statusFilter, reviewerFilter], () => { currentPage.value = 1 })
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function toggleDetails(id) {
  expandedId.value = expandedId.value === id ? '' : id
}
</script>

<template>
  <div class="space-y-5">
    <section>
      <p class="text-sm text-muted">Kiểm duyệt</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Theo dõi kiểm duyệt</h2>
      <p class="mt-2 text-sm leading-6 text-muted">Admin xem tiến độ, Reviewer phụ trách và ghi chú; không có thao tác phê duyệt, từ chối hoặc yêu cầu chỉnh sửa tại đây.</p>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Thống kê trạng thái kiểm duyệt">
      <article v-for="summary in statusCounts" :key="summary.status" class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-xs text-muted">{{ REVIEW_STATUS_LABELS[summary.status] }}</p>
        <p class="mt-2 text-2xl font-bold text-navy">{{ summary.count }}</p>
      </article>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 xl:grid-cols-[minmax(240px,1fr)_170px_190px_210px]">
        <SearchInput v-model="query" label="Tìm lịch sử kiểm duyệt" placeholder="Tên, người cung cấp, Reviewer, ghi chú..." />
        <label class="sr-only" for="monitor-type">Loại nội dung</label>
        <select id="monitor-type" v-model="typeFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả nội dung</option>
          <option value="course">Khóa học</option>
          <option value="material">Tài liệu</option>
        </select>
        <label class="sr-only" for="monitor-status">Trạng thái kiểm duyệt</label>
        <select id="monitor-status" v-model="statusFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả trạng thái</option>
          <option v-for="(label, status) in REVIEW_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
        </select>
        <label class="sr-only" for="monitor-reviewer">Reviewer</label>
        <select id="monitor-reviewer" v-model="reviewerFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả Reviewer</option>
          <option v-for="reviewer in reviewers" :key="reviewer" :value="reviewer">{{ reviewer }}</option>
        </select>
      </div>

      <div v-if="visibleRecords.length" class="overflow-x-auto">
        <table class="w-full min-w-[1050px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Nội dung</th>
              <th scope="col" class="px-4 py-3 font-semibold">Loại</th>
              <th scope="col" class="px-4 py-3 font-semibold">Người cung cấp</th>
              <th scope="col" class="px-4 py-3 font-semibold">Reviewer</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ngày gửi</th>
              <th scope="col" class="px-4 py-3 font-semibold">Phân công</th>
              <th scope="col" class="px-4 py-3 font-semibold">Cập nhật gần nhất</th>
              <th scope="col" class="px-4 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ghi chú</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="record in visibleRecords" :key="record.id">
              <tr class="align-top">
                <th scope="row" class="max-w-64 px-4 py-3.5">
                  <span class="block line-clamp-2 font-semibold text-navy">{{ record.title }}</span>
                  <span class="mt-1 block text-xs font-normal text-muted">{{ record.id }}</span>
                </th>
                <td class="px-4 py-3.5 text-muted">{{ record.itemType === 'course' ? 'Khóa học' : 'Tài liệu' }}</td>
                <td class="px-4 py-3.5 text-muted">{{ record.creator || 'Chưa có dữ liệu' }}</td>
                <td class="px-4 py-3.5 text-muted">{{ record.reviewerName || 'Chưa phân công' }}</td>
                <td class="whitespace-nowrap px-4 py-3.5 text-muted">{{ formatDate(record.submittedAt) }}</td>
                <td class="whitespace-nowrap px-4 py-3.5 text-muted">{{ formatDate(record.assignedAt) }}</td>
                <td class="whitespace-nowrap px-4 py-3.5 text-muted">{{ formatDate(record.completedAt || record.reviewedAt) }}</td>
                <td class="px-4 py-3.5"><span class="rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-muted">{{ REVIEW_STATUS_LABELS[record.status] || 'Chưa xác định' }}</span></td>
                <td class="px-4 py-3.5">
                  <button type="button" class="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline" :aria-expanded="expandedId === record.id" @click="toggleDetails(record.id)">
                    <FileSearch :size="14" aria-hidden="true" /> {{ expandedId === record.id ? 'Ẩn' : 'Xem' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedId === record.id" class="bg-background/70">
                <td colspan="9" class="px-4 py-4">
                  <p class="text-xs font-semibold uppercase tracking-wide text-muted">Ghi chú của Reviewer</p>
                  <p class="mt-2 whitespace-pre-line text-sm leading-6 text-navy">{{ record.note || 'Chưa có ghi chú.' }}</p>
                  <p v-if="record.reviewNote" class="mt-2 text-xs text-muted">Bản ghi kiểm duyệt trong dữ liệu mẫu.</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="Không có kết quả phù hợp" description="Thay đổi bộ lọc hoặc từ khóa để xem thêm dữ liệu." />
      <PaginationControls v-if="filteredRecords.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredRecords.length" />
    </section>
  </div>
</template>
