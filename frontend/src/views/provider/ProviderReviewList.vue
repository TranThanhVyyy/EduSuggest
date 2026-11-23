<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import {
  PROVIDER_STATUS_LABELS,
} from '@/service/providerApiService'
import { loadProviderCourses, loadProviderReviews, mapProviderReview, providerErrorMessage } from '@/service/providerApiService'

const route = useRoute()
const pageSize = 8
const query = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const records = ref([])
const isLoading = ref(true)
const loadError = ref('')
const isHistory = computed(() => route.name === 'provider-review-history')

async function refreshRecords() {
  isLoading.value = true
  loadError.value = ''
  try {
    const courses = await loadProviderCourses()
    if (!isHistory.value) {
      records.value = courses.filter((course) => course.status !== 'Draft')
    } else {
      const histories = await Promise.all(courses.map(async (course) => {
        const reviews = await loadProviderReviews(course.id)
        return reviews.map(mapProviderReview).map((review) => ({
          id: String(review.maDanhGia),
          courseId: course.id,
          title: course.title,
          category: course.category,
          status: review.status,
          action: review.action,
          createdAt: review.createdAt,
          feedback: review.feedback,
        }))
      }))
      records.value = histories.flat().sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    }
  } catch (error) {
    loadError.value = providerErrorMessage(error, 'Không thể tải dữ liệu kiểm duyệt từ Backend.')
  } finally {
    isLoading.value = false
  }
}

refreshRecords()
const filteredRecords = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return records.value.filter((record) => {
    const text = `${record.id} ${record.title} ${record.category} ${record.reviewerName} ${record.reviewFeedback || record.feedback || ''} ${record.action || ''}`.toLocaleLowerCase('vi')
    return (!search || text.includes(search)) && (!statusFilter.value || record.status === statusFilter.value)
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRecords.value.length / pageSize)))
const visibleRecords = computed(() =>
  filteredRecords.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch([query, statusFilter, isHistory], () => { currentPage.value = 1 })
watch(isHistory, refreshRecords)
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
</script>

<template>
  <div class="space-y-5">
    <section>
      <p class="text-sm text-muted">Kiểm duyệt</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ isHistory ? 'Lịch sử kiểm duyệt' : 'Theo dõi kiểm duyệt' }}</h2>
      <p class="mt-2 text-sm leading-6 text-muted">{{ isHistory ? 'Các khóa học đã gửi và các mốc lịch sử có dữ liệu.' : 'Theo dõi trạng thái, thời gian gửi, Reviewer và phản hồi nếu dữ liệu hiện có.' }}</p>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(240px,1fr)_230px]">
        <SearchInput v-model="query" label="Tìm khóa học kiểm duyệt" placeholder="Tên, mã, danh mục, Reviewer..." />
        <label class="sr-only" for="provider-review-status">Lọc trạng thái kiểm duyệt</label>
        <select id="provider-review-status" v-model="statusFilter" class="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả trạng thái</option>
          <option v-for="(label, status) in PROVIDER_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
        </select>
      </div>
      <p v-if="isLoading" class="p-5 text-sm text-muted" role="status">Đang tải dữ liệu kiểm duyệt…</p>
      <p v-else-if="loadError" class="m-4 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-primary" role="alert">{{ loadError }} <button type="button" class="ml-2 font-semibold underline" @click="refreshRecords">Thử lại</button></p>
      <div v-else-if="visibleRecords.length" class="overflow-x-auto">
        <table class="w-full min-w-[900px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Khóa học</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ngày gửi</th>
              <th scope="col" class="px-4 py-3 font-semibold">Reviewer phụ trách</th>
              <th scope="col" class="px-4 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="px-4 py-3 font-semibold">Phản hồi</th>
              <th scope="col" class="px-4 py-3 font-semibold">Chi tiết</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="record in visibleRecords" :key="record.id" class="align-top hover:bg-background/70">
              <th scope="row" class="max-w-72 px-4 py-4">
                <RouterLink :to="{ name: 'provider-review-detail', params: { id: isHistory ? record.courseId : record.id } }" class="font-semibold text-primary hover:underline">{{ record.title || 'Khóa học chưa đặt tên' }}</RouterLink>
                <span class="mt-1 block text-xs font-normal text-muted">{{ isHistory ? record.action : record.category || 'Chưa có danh mục' }}</span>
              </th>
              <td class="whitespace-nowrap px-4 py-4 text-muted">{{ formatDate(isHistory ? record.createdAt : record.submittedAt) }}</td>
              <td class="px-4 py-4 text-muted">{{ record.reviewerName || 'Chưa có dữ liệu phân công' }}</td>
              <td class="px-4 py-4"><span class="inline-flex rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-navy">{{ PROVIDER_STATUS_LABELS[record.status] || record.status }}</span></td>
              <td class="max-w-60 px-4 py-4 text-muted">{{ isHistory ? (record.feedback || 'Chưa có phản hồi được lưu.') : (record.reviewFeedback || 'Chưa có nhận xét được lưu.') }}</td>
              <td class="px-4 py-4"><RouterLink :to="{ name: 'provider-review-detail', params: { id: isHistory ? record.courseId : record.id } }" class="text-xs font-semibold text-primary hover:underline">{{ isHistory ? 'Xem mốc' : 'Xem tiến trình' }}</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else :title="isHistory ? 'Chưa có lịch sử kiểm duyệt' : 'Chưa có khóa học gửi kiểm duyệt'" description="Khóa học chỉ xuất hiện sau khi được gửi. Không có phản hồi nào được tạo giả." />
      <PaginationControls v-if="filteredRecords.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredRecords.length" />
    </section>
  </div>
</template>
