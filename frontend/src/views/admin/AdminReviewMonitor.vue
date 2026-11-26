<script setup>
import { onMounted, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, RefreshCw, RotateCcw } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  extractApiError,
  fetchAdminQueueJobs,
  formatDateTimeVi,
  retryAdminQueueJob,
} from '@/service/adminPhase3ApiService'

const QUEUE_STATUSES = [
  { key: '', label: 'Tất cả', tone: 'neutral' },
  { key: 'PENDING', label: 'PENDING', tone: 'warning' },
  { key: 'PROCESSING', label: 'PROCESSING', tone: 'info' },
  { key: 'RETRYING', label: 'RETRYING', tone: 'amber' },
  { key: 'WAITING_ELIGIBLE', label: 'WAITING_ELIGIBLE', tone: 'navy' },
  { key: 'DONE', label: 'DONE', tone: 'success' },
  { key: 'FAILED', label: 'FAILED', tone: 'danger' },
  { key: 'CANCELLED', label: 'CANCELLED', tone: 'neutral' },
]

const loading = ref(true)
const error = ref('')
const feedback = ref('')
const jobs = ref([])
const statusFilter = ref('')
const targetTypeFilter = ref('')
const limit = 25
const offset = ref(0)
const retryBusyId = ref(null)

function toneFor(status) {
  return QUEUE_STATUSES.find((s) => s.key === status)?.tone || 'neutral'
}

function canRetry(job) {
  return ['WAITING_ELIGIBLE', 'FAILED', 'RETRYING'].includes(job.trangThai)
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchAdminQueueJobs({
      status: statusFilter.value,
      targetType: targetTypeFilter.value,
      limit,
      offset: offset.value,
    })
    jobs.value = Array.isArray(res) ? res : []
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải danh sách hàng đợi phân công.')
  } finally {
    loading.value = false
  }
}

async function handleRetry(job) {
  if (retryBusyId.value) return
  retryBusyId.value = job.maCongViec
  error.value = ''
  feedback.value = ''
  try {
    await retryAdminQueueJob(job.maCongViec)
    feedback.value = `Đã kích hoạt xử lý lại công việc hàng đợi #${job.maCongViec}.`
    await loadData()
  } catch (err) {
    error.value = extractApiError(err, `Không thể thử lại công việc #${job.maCongViec}.`)
  } finally {
    retryBusyId.value = null
  }
}

watch([statusFilter, targetTypeFilter], () => {
  offset.value = 0
  loadData()
})

onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Hàng đợi PostgreSQL</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Giám sát hàng đợi phân công</h1>
        <p class="mt-1 text-sm text-muted">
          Theo dõi 7 trạng thái bảng HangDoiPhanCong, lý do chờ, số lần thử và kích hoạt xử lý lại an toàn.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <RouterLink
          :to="{ name: 'admin-assign-reviewer' }"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy hover:bg-subtle"
        >
          Danh sách phân công
        </RouterLink>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white hover:bg-navy/90"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Status Pills + Target Filter -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap gap-1.5" role="tablist" aria-label="Lọc trạng thái hàng đợi">
        <button
          v-for="st in QUEUE_STATUSES"
          :key="st.key || 'ALL'"
          type="button"
          role="tab"
          :aria-selected="statusFilter === st.key"
          class="rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors"
          :class="
            statusFilter === st.key
              ? 'border-navy bg-navy text-white'
              : 'border-border bg-surface text-slate-600 hover:bg-subtle hover:text-navy'
          "
          @click="statusFilter = st.key"
        >
          {{ st.label }}
        </button>
      </div>

      <select
        v-model="targetTypeFilter"
        aria-label="Lọc loại đối tượng hàng đợi"
        class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả loại đối tượng</option>
        <option value="COURSE">COURSE</option>
        <option value="MATERIAL">MATERIAL</option>
      </select>
    </div>

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <UiEmptyState
      v-else-if="jobs.length === 0"
      title="Không có công việc hàng đợi phù hợp"
      description="Hàng đợi HangDoiPhanCong hiện không có bản ghi nào khớp với bộ lọc đang chọn."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-left text-xs">
        <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
          <tr>
            <th class="px-4 py-3">Job / Đối tượng</th>
            <th class="px-4 py-3">Sự kiện / Vòng</th>
            <th class="px-4 py-3">Trạng thái</th>
            <th class="px-4 py-3">Số lần thử</th>
            <th class="px-4 py-3">Chạy tiếp theo</th>
            <th class="px-4 py-3">Nguyên nhân / Lỗi gần nhất</th>
            <th class="px-4 py-3 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/70">
          <tr v-for="job in jobs" :key="job.maCongViec" class="hover:bg-subtle/40">
            <td class="px-4 py-3">
              <p class="font-mono font-bold text-navy">#{{ job.maCongViec }}</p>
              <p class="text-[11px] text-muted">
                {{ job.loaiDoiTuong }} #{{ job.maKhoaHoc ?? job.maTaiLieu }}
              </p>
            </td>

            <td class="px-4 py-3">
              <span class="rounded bg-subtle px-1.5 py-0.5 font-mono text-[10px] font-semibold text-navy">
                {{ job.loaiSuKien }}
              </span>
              <p class="mt-1 text-[11px] text-muted">Vòng {{ job.soVongKiemDuyet }}</p>
            </td>

            <td class="px-4 py-3">
              <UiStatusBadge :tone="toneFor(job.trangThai)" :label="job.trangThai" />
            </td>

            <td class="px-4 py-3 font-mono font-semibold text-navy tabular-nums">
              {{ job.soLanThu }} / {{ job.soLanThuToiDa }}
            </td>

            <td class="px-4 py-3 tabular-nums text-ink">
              {{ formatDateTimeVi(job.thoiDiemChayTiepTheo) }}
            </td>

            <td class="px-4 py-3 max-w-xs">
              <p v-if="job.lyDoCho" class="text-amber-dark font-medium">{{ job.lyDoCho }}</p>
              <p v-if="job.loiGanNhat" class="text-danger">{{ job.loiGanNhat }}</p>
              <span v-if="!job.lyDoCho && !job.loiGanNhat" class="text-muted">—</span>
            </td>

            <td class="px-4 py-3 text-right">
              <button
                v-if="canRetry(job)"
                type="button"
                class="inline-flex items-center gap-1 rounded-lg bg-teal px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50"
                :disabled="retryBusyId === job.maCongViec"
                @click="handleRetry(job)"
              >
                <RotateCcw :size="13" aria-hidden="true" />
                <span>{{ retryBusyId === job.maCongViec ? 'Đang gửi...' : 'Thử lại' }}</span>
              </button>
              <span v-else class="text-[11px] text-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between">
      <p class="text-xs text-muted tabular-nums">Hiển thị {{ jobs.length }} bản ghi (offset {{ offset }})</p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="offset === 0"
          @click="offset = Math.max(0, offset - limit); loadData()"
        >
          <ChevronLeft :size="14" aria-hidden="true" />
          <span>Trước</span>
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="jobs.length < limit"
          @click="offset += limit; loadData()"
        >
          <span>Sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </div>
    </div>
  </section>
</template>
