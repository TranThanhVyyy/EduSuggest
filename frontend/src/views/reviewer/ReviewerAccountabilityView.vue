<script setup>
import { onMounted, ref, watch } from 'vue'
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatCard from '@/components/ui/UiStatCard.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'
import {
  extractApiError,
  fetchAccountabilityPolicy,
  fetchMyAccountabilitySummary,
  fetchMyViolations,
} from '@/service/expertPhase3ApiService'

const loading = ref(true)
const error = ref('')
const summary = ref(null)
const policy = ref(null)
const violations = ref([])
const statusFilter = ref('')

const DISCIPLINE_META = {
  NORMAL: { label: 'Bình thường', tone: 'success' },
  WARNING: { label: 'Cảnh báo', tone: 'warning' },
  FINAL_WARNING: { label: 'Cảnh báo cuối', tone: 'amber' },
  LOCKED: { label: 'Tài khoản bị khóa', tone: 'danger' },
}

const VIOLATION_STATUS_META = {
  PENDING_REVIEW: { label: 'Chờ ADMIN xem xét', tone: 'warning' },
  CONFIRMED: { label: 'Đã xác nhận vi phạm', tone: 'danger' },
  EXEMPTED: { label: 'Đã miễn trừ', tone: 'success' },
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [sumRes, polRes, vpRes] = await Promise.all([
      fetchMyAccountabilitySummary(),
      fetchAccountabilityPolicy(),
      fetchMyViolations({ status: statusFilter.value, limit: 50 }),
    ])
    summary.value = sumRes
    policy.value = polRes
    violations.value = Array.isArray(vpRes) ? vpRes : []
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải thông tin kỷ luật và lịch sử vi phạm.')
  } finally {
    loading.value = false
  }
}

watch(statusFilter, loadData)
onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Trách nhiệm kiểm duyệt</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Kỷ luật & Lịch sử vi phạm</h1>
        <p class="mt-1 text-sm text-muted">
          Theo dõi số vi phạm hợp lệ trong cửa sổ trượt và kết quả xác minh từ Quản trị viên (chỉ đọc).
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy hover:bg-subtle"
        :disabled="loading"
        @click="loadData"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />

    <UiAlert
      v-if="policy"
      variant="info"
      title="Chính sách kỷ luật hiện hành"
      :message="`Cửa sổ thống kê: ${policy.windowHours} giờ liên tục · Cảnh báo từ ${policy.warningThreshold} vi phạm · Cảnh báo cuối ở ${policy.finalWarningThreshold} vi phạm · Tự động khóa từ ${policy.lockThreshold} vi phạm CONFIRMED (chỉ ADMIN có quyền mở khóa). Việc đánh giá REJECTED hoặc NEEDS_REVISION cho khóa học KHÔNG phải vi phạm kỷ luật.`"
    />

    <div v-if="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UiSkeleton v-for="i in 4" :key="i" variant="rect" height="112px" rounded="12px" />
    </div>

    <template v-else-if="summary">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <UiStatCard
          title="Vi phạm CONFIRMED"
          :value="`${summary.confirmedViolationsInWindow} / ${summary.lockThreshold}`"
          :description="`Trong cửa sổ ${summary.windowHours} giờ`"
          :icon="ShieldAlert"
          variant="primary"
          size="sm"
        />
        <UiStatCard
          title="Còn lại trước ngưỡng khóa"
          :value="summary.remainingBeforeLock"
          description="Số vi phạm còn lại ở chu kỳ hiện tại"
          :icon="AlertTriangle"
          :variant="summary.remainingBeforeLock <= 1 ? 'amber' : 'teal'"
          size="sm"
        />
        <UiStatCard
          title="Chờ ADMIN xem xét"
          :value="summary.pendingReviewCount"
          description="Trạng thái PENDING_REVIEW"
          size="sm"
        />
        <UiStatCard
          title="Chu kỳ kỷ luật"
          :value="`Chu kỳ #${summary.currentCycle}`"
          :description="DISCIPLINE_META[summary.disciplineLevel]?.label || summary.disciplineLevel"
          size="sm"
        />
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-xs">
          <span class="font-semibold text-navy">Mức cảnh báo hiện tại:</span>
          <UiStatusBadge
            :tone="DISCIPLINE_META[summary.disciplineLevel]?.tone || 'neutral'"
            :label="DISCIPLINE_META[summary.disciplineLevel]?.label || summary.disciplineLevel"
          />
        </div>

        <select
          v-model="statusFilter"
          aria-label="Lọc trạng thái vi phạm"
          class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-ink focus:border-teal focus:outline-none"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="PENDING_REVIEW">Chờ xem xét (PENDING_REVIEW)</option>
          <option value="CONFIRMED">Đã xác nhận (CONFIRMED)</option>
          <option value="EXEMPTED">Đã miễn trừ (EXEMPTED)</option>
        </select>
      </div>

      <UiEmptyState
        v-if="violations.length === 0"
        title="Không có bản ghi vi phạm"
        description="Bạn chưa có vi phạm nào khớp với bộ lọc đang chọn."
      />

      <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-left text-xs">
          <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th class="px-4 py-3">Mã / Nhiệm vụ</th>
              <th class="px-4 py-3">Loại vi phạm / Lý do</th>
              <th class="px-4 py-3">Chu kỳ</th>
              <th class="px-4 py-3">Thời điểm</th>
              <th class="px-4 py-3">Trạng thái</th>
              <th class="px-4 py-3">Phản hồi từ ADMIN</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/70">
            <tr v-for="vp in violations" :key="vp.maViPham" class="hover:bg-subtle/40">
              <td class="px-4 py-3 font-mono font-bold text-navy">VP#{{ vp.maViPham }} · PC#{{ vp.maPhanCong }}</td>
              <td class="px-4 py-3 max-w-sm">
                <p class="font-semibold text-navy">{{ vp.loaiViPham }}</p>
                <p v-if="vp.maLyDoTuChoi" class="font-mono text-[11px] text-muted">{{ vp.maLyDoTuChoi }}</p>
                <p v-if="vp.lyDo" class="mt-0.5 text-slate-600">{{ vp.lyDo }}</p>
              </td>
              <td class="px-4 py-3 font-mono text-navy">#{{ vp.chuKyKyLuatSo }}</td>
              <td class="px-4 py-3 tabular-nums text-ink">{{ formatDateTimeVi(vp.ngayViPham) }}</td>
              <td class="px-4 py-3">
                <UiStatusBadge
                  :tone="VIOLATION_STATUS_META[vp.trangThaiXuLy]?.tone || 'neutral'"
                  :label="VIOLATION_STATUS_META[vp.trangThaiXuLy]?.label || vp.trangThaiXuLy"
                />
              </td>
              <td class="px-4 py-3 max-w-xs text-slate-600">{{ vp.ghiChuXuLy || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>
