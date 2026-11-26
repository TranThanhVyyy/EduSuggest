<script setup>
import { computed, onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { getExpertReviewHistory } from '@/service/expertApiService'

const history = ref([])
const query = ref('')
const statusFilter = ref('')
const loading = ref(true)
const errorMessage = ref('')

const filteredHistory = computed(() => {
  const q = query.value.trim().toLocaleLowerCase('vi')
  return history.value.filter((record) => {
    const matchesStatus = !statusFilter.value || record.status === statusFilter.value
    const matchesQuery =
      !q ||
      `${record.id} ${record.title} ${record.note}`.toLocaleLowerCase('vi').includes(q)
    return matchesStatus && matchesQuery
  })
})

async function loadHistory() {
  loading.value = true
  errorMessage.value = ''
  try {
    history.value = await getExpertReviewHistory()
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải lịch sử kiểm duyệt.'
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Nhật ký thẩm định</p>
        <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">Lịch sử kiểm duyệt</h1>
        <p class="mt-1.5 text-sm text-slate-600">
          Toàn bộ quyết định phê duyệt, yêu cầu chỉnh sửa và từ chối bạn đã thực hiện.
        </p>
      </div>

      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
        :disabled="loading"
        @click="loadHistory"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </section>

    <section class="overflow-hidden rounded-2xl border border-border bg-surface shadow-xs">
      <div class="grid gap-3 border-b border-border/80 px-5 py-3.5 md:grid-cols-[minmax(240px,1fr)_220px]">
        <SearchInput v-model="query" label="Tìm lịch sử kiểm duyệt" placeholder="Tìm theo tên nội dung hoặc ghi chú..." />
        <label class="sr-only" for="reviewer-history-status">Lọc theo kết quả</label>
        <select
          id="reviewer-history-status"
          v-model="statusFilter"
          class="min-w-0 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-navy outline-none focus:border-teal focus:ring-2 focus:ring-teal/15"
        >
          <option value="">Tất cả kết quả</option>
          <option value="DaPheDuyet">Đã phê duyệt</option>
          <option value="YeuCauChinhSua">Yêu cầu chỉnh sửa</option>
          <option value="TuChoi">Từ chối</option>
        </select>
      </div>

      <div v-if="loading" class="space-y-3 p-5">
        <UiSkeleton v-for="i in 4" :key="i" variant="rect" height="52px" rounded="0.75rem" />
      </div>

      <div v-else-if="errorMessage" class="p-5">
        <p class="rounded-xl border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-danger" role="alert">
          {{ errorMessage }}
          <button type="button" class="ml-2 font-semibold underline" @click="loadHistory">Thử lại</button>
        </p>
      </div>

      <div v-else-if="filteredHistory.length" class="overflow-x-auto">
        <table class="w-full min-w-[740px] text-left text-sm">
          <thead class="border-b border-border/80 bg-background text-[11px] uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th scope="col" class="whitespace-nowrap px-5 py-3 font-semibold">Nội dung</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">Loại</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">Kết quả</th>
              <th scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">Thời gian</th>
              <th scope="col" class="whitespace-nowrap px-5 py-3 font-semibold">Ghi chú</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr
              v-for="record in filteredHistory"
              :key="record.id"
              class="align-middle transition-colors duration-150 hover:bg-background/70"
            >
              <th scope="row" class="px-5 py-4 font-semibold text-navy">
                {{ record.title }}
              </th>
              <td class="whitespace-nowrap px-4 py-4">
                <span
                  class="inline-flex rounded px-2 py-0.5 text-[11px] font-bold uppercase"
                  :class="record.itemType === 'material' ? 'bg-teal/10 text-teal-dark' : 'bg-navy/10 text-navy'"
                >
                  {{ record.itemType === 'material' ? 'Tài liệu' : 'Khóa học' }}
                </span>
              </td>
              <td class="whitespace-nowrap px-4 py-4">
                <UiStatusBadge :status="record.status" />
              </td>
              <td class="whitespace-nowrap px-4 py-4 text-xs text-slate-500 tabular-nums">
                {{ formatDate(record.reviewedAt) }}
              </td>
              <td class="max-w-xs px-5 py-4 text-xs text-slate-600">
                {{ record.note || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-6">
        <EmptyState
          title="Chưa có lịch sử kiểm duyệt"
          :description="query || statusFilter ? 'Không có bản ghi phù hợp với bộ lọc hiện tại.' : 'Các quyết định bạn thực hiện sẽ được lưu tại đây.'"
        />
      </div>
    </section>
  </div>
</template>
