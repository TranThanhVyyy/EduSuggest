<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  Activity,
  AlertTriangle,
  CalendarOff,
  CheckCircle2,
  Clock,
  Layers,
  Lock,
  RefreshCw,
  ShieldAlert,
  UserCheck,
  Users,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatCard from '@/components/ui/UiStatCard.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  extractApiError,
  fetchAdminWorkload,
  fetchExpertOverview,
  formatDateTimeVi,
} from '@/service/adminPhase3ApiService'

const loading = ref(true)
const error = ref('')
const overview = ref(null)
const workload = ref([])

const ASSIGNMENT_STATUS_LABELS = {
  ASSIGNED: { label: 'Chờ tiếp nhận', bar: 'bg-amber' },
  ACCEPTED: { label: 'Đã tiếp nhận', bar: 'bg-info' },
  IN_PROGRESS: { label: 'Đang kiểm duyệt', bar: 'bg-teal' },
  COMPLETED: { label: 'Hoàn thành', bar: 'bg-success' },
  DECLINED: { label: 'Từ chối', bar: 'bg-danger' },
  EXPIRED: { label: 'Quá hạn tiếp nhận', bar: 'bg-danger/70' },
  CANCELLED: { label: 'Đã thu hồi', bar: 'bg-slate-400' },
}

const QUEUE_STATUS_LABELS = {
  PENDING: { label: 'PENDING (Chờ xử lý)', bar: 'bg-amber' },
  PROCESSING: { label: 'PROCESSING (Đang chạy)', bar: 'bg-info' },
  RETRYING: { label: 'RETRYING (Thử lại)', bar: 'bg-amber-dark' },
  WAITING_ELIGIBLE: { label: 'WAITING_ELIGIBLE (Chờ chuyên gia)', bar: 'bg-navy' },
  DONE: { label: 'DONE (Hoàn tất)', bar: 'bg-success' },
  FAILED: { label: 'FAILED (Lỗi)', bar: 'bg-danger' },
  CANCELLED: { label: 'CANCELLED (Đã hủy)', bar: 'bg-slate-400' },
}

const DISCIPLINE_LABELS = {
  NORMAL: { label: 'Bình thường', tone: 'success' },
  WARNING: { label: 'Cảnh báo', tone: 'warning' },
  FINAL_WARNING: { label: 'Cảnh báo cuối', tone: 'amber' },
  LOCKED: { label: 'Đang bị khóa', tone: 'danger' },
}

const assignmentRows = computed(() => {
  const map = overview.value?.assignmentStatusBreakdown || {}
  const total = Object.values(map).reduce((a, b) => a + Number(b || 0), 0)
  return Object.entries(ASSIGNMENT_STATUS_LABELS).map(([key, meta]) => {
    const count = Number(map[key] || 0)
    const pct = total > 0 ? Math.round((count / total) * 100) : 0
    return { key, ...meta, count, pct }
  })
})

const queueRows = computed(() => {
  const map = overview.value?.queueStatusBreakdown || {}
  const total = Object.values(map).reduce((a, b) => a + Number(b || 0), 0)
  return Object.entries(QUEUE_STATUS_LABELS).map(([key, meta]) => {
    const count = Number(map[key] || 0)
    const pct = total > 0 ? Math.round((count / total) * 100) : 0
    return { key, ...meta, count, pct }
  })
})

const disciplineRows = computed(() => {
  const map = overview.value?.disciplineLevelBreakdown || {}
  return Object.entries(DISCIPLINE_LABELS).map(([key, meta]) => ({
    key,
    ...meta,
    count: Number(map[key] || 0),
  }))
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [ov, wl] = await Promise.all([fetchExpertOverview(), fetchAdminWorkload()])
    overview.value = ov
    workload.value = Array.isArray(wl) ? wl : []
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải dữ liệu tổng quan quản lý chuyên gia.')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Điều hành kiểm duyệt</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Tổng quan quản lý chuyên gia</h1>
        <p class="mt-1 text-sm text-muted">
          Số liệu thời gian thực từ cơ sở dữ liệu về đội ngũ chuyên gia, phân công, hàng đợi và kỷ luật.
          <span v-if="overview?.evaluatedAt" class="ml-1 tabular-nums">
            (Cập nhật: {{ formatDateTimeVi(overview.evaluatedAt) }})
          </span>
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy transition-colors hover:bg-subtle"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
        <RouterLink
          :to="{ name: 'admin-reviewers' }"
          class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-navy/90"
        >
          <Users :size="14" aria-hidden="true" />
          <span>Quản lý hồ sơ chuyên gia</span>
        </RouterLink>
      </div>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />

    <div v-if="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <UiSkeleton v-for="i in 10" :key="i" variant="rect" height="112px" rounded="12px" />
    </div>

    <template v-else-if="overview">
      <!-- 10 KPI Bento Grid -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <UiStatCard
          title="Tổng chuyên gia"
          :value="overview.totalExperts"
          description="Tài khoản vai trò EXPERT"
          :icon="Users"
          variant="primary"
          size="sm"
        />
        <UiStatCard
          title="Đã xác minh"
          :value="overview.verifiedExperts"
          description="Hồ sơ VERIFIED đủ điều kiện"
          :icon="UserCheck"
          variant="teal"
          size="sm"
        />
        <UiStatCard
          title="Chờ xác minh"
          :value="overview.pendingVerificationExperts"
          description="Cần ADMIN thẩm định hồ sơ"
          :icon="Clock"
          variant="amber"
          size="sm"
        />
        <UiStatCard
          title="Đang nhận nhiệm vụ"
          :value="overview.activeWorkingExperts"
          description="Có ít nhất 1 nhiệm vụ mở"
          :icon="Activity"
          size="sm"
        />
        <UiStatCard
          title="Đang tạm ngừng"
          :value="overview.pausedExperts"
          description="Trong khoảng APPROVED"
          :icon="CalendarOff"
          size="sm"
        />
        <UiStatCard
          title="Đang bị khóa"
          :value="overview.lockedExperts"
          description="Tài khoản LOCKED"
          :icon="Lock"
          size="sm"
        />
        <UiStatCard
          title="Nhiệm vụ đang duyệt"
          :value="overview.activeAssignments"
          description="ASSIGNED / ACCEPTED / IN_PROGRESS"
          :icon="CheckCircle2"
          variant="teal"
          size="sm"
        />
        <UiStatCard
          title="Nhiệm vụ quá hạn"
          :value="overview.overdueAssignments"
          description="Vượt hạn tiếp nhận hoặc duyệt"
          :icon="AlertTriangle"
          variant="amber"
          size="sm"
        />
        <UiStatCard
          title="Chờ phân công"
          :value="overview.pendingQueueJobs"
          description="Job đang mở trong hàng đợi"
          :icon="Layers"
          size="sm"
        />
        <UiStatCard
          title="Vi phạm cần xem xét"
          :value="overview.pendingViolations"
          description="Trạng thái PENDING_REVIEW"
          :icon="ShieldAlert"
          variant="amber"
          size="sm"
        />
      </div>

      <!-- Analytical Panels: 2x2 Bento -->
      <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <!-- 1. Workload Distribution -->
        <section class="rounded-xl border border-border bg-surface p-5">
          <div class="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
            <div>
              <h2 class="text-sm font-bold text-navy">Phân bố tải công việc</h2>
              <p class="text-xs text-muted">Số nhiệm vụ đang mở so với trần tải tối đa</p>
            </div>
            <RouterLink :to="{ name: 'admin-assign-reviewer' }" class="text-xs font-semibold text-teal hover:underline">
              Xem phân công
            </RouterLink>
          </div>

          <UiEmptyState
            v-if="workload.length === 0"
            class="mt-4"
            title="Chưa có dữ liệu tải chuyên gia"
            description="Chưa có tài khoản EXPERT nào trong cơ sở dữ liệu."
          />

          <div v-else class="mt-4 space-y-3 max-h-72 overflow-y-auto pr-1">
            <div v-for="item in workload" :key="item.maChuyenGia" class="space-y-1">
              <div class="flex items-center justify-between gap-2 text-xs">
                <span class="truncate font-semibold text-navy">
                  {{ item.hoTen || `Chuyên gia #${item.maChuyenGia}` }}
                </span>
                <div class="flex shrink-0 items-center gap-2">
                  <UiStatusBadge
                    :tone="item.trangThaiTaiKhoan === 'LOCKED' ? 'danger' : item.trangThaiHoSo === 'VERIFIED' ? 'success' : 'warning'"
                    :label="item.trangThaiTaiKhoan === 'LOCKED' ? 'LOCKED' : item.trangThaiHoSo"
                  />
                  <span class="font-mono font-semibold text-navy tabular-nums">
                    {{ item.activeAssignments }}/{{ item.maxAssignments }}
                  </span>
                </div>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
                <div
                  class="h-full rounded-full transition-all"
                  :class="item.activeAssignments >= item.maxAssignments ? 'bg-amber' : 'bg-teal'"
                  :style="{ width: `${Math.min(100, item.maxAssignments > 0 ? Math.round((item.activeAssignments / item.maxAssignments) * 100) : 0)}%` }"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- 2. Assignment Status Breakdown -->
        <section class="rounded-xl border border-border bg-surface p-5">
          <div class="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
            <div>
              <h2 class="text-sm font-bold text-navy">Trạng thái nhiệm vụ kiểm duyệt</h2>
              <p class="text-xs text-muted">Thống kê trên toàn bộ bảng PhanCongKiemDuyet</p>
            </div>
            <RouterLink :to="{ name: 'admin-assign-reviewer' }" class="text-xs font-semibold text-teal hover:underline">
              Chi tiết
            </RouterLink>
          </div>
          <div class="mt-4 space-y-3">
            <div v-for="row in assignmentRows" :key="row.key" class="space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="font-medium text-ink">{{ row.label }}</span>
                <span class="font-mono font-semibold text-navy tabular-nums">{{ row.count }} ({{ row.pct }}%)</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
                <div class="h-full rounded-full" :class="row.bar" :style="{ width: `${row.pct}%` }" />
              </div>
            </div>
          </div>
        </section>

        <!-- 3. Durable Queue Breakdown -->
        <section class="rounded-xl border border-border bg-surface p-5">
          <div class="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
            <div>
              <h2 class="text-sm font-bold text-navy">Tình trạng hàng đợi phân công</h2>
              <p class="text-xs text-muted">Phân bố 7 trạng thái bảng HangDoiPhanCong</p>
            </div>
            <RouterLink :to="{ name: 'admin-review-monitor' }" class="text-xs font-semibold text-teal hover:underline">
              Giám sát hàng đợi
            </RouterLink>
          </div>
          <div class="mt-4 space-y-3">
            <div v-for="row in queueRows" :key="row.key" class="space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="font-medium text-ink">{{ row.label }}</span>
                <span class="font-mono font-semibold text-navy tabular-nums">{{ row.count }} ({{ row.pct }}%)</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
                <div class="h-full rounded-full" :class="row.bar" :style="{ width: `${row.pct}%` }" />
              </div>
            </div>
          </div>
        </section>

        <!-- 4. Discipline & Availability Quick Actions -->
        <section class="rounded-xl border border-border bg-surface p-5 flex flex-col justify-between gap-4">
          <div>
            <div class="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
              <div>
                <h2 class="text-sm font-bold text-navy">Tình trạng kỷ luật chuyên gia</h2>
                <p class="text-xs text-muted">Phân loại mức cảnh báo trong cửa sổ 168 giờ hiện tại</p>
              </div>
              <RouterLink :to="{ name: 'admin-accountability' }" class="text-xs font-semibold text-teal hover:underline">
                Mở kỷ luật
              </RouterLink>
            </div>
            <div class="mt-4 grid grid-cols-2 gap-3">
              <div
                v-for="item in disciplineRows"
                :key="item.key"
                class="flex items-center justify-between rounded-lg border border-border bg-subtle/40 px-3.5 py-3"
              >
                <UiStatusBadge :tone="item.tone" :label="item.label" />
                <span class="text-lg font-bold text-navy tabular-nums">{{ item.count }}</span>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-subtle/60 px-4 py-3 text-xs">
            <span class="font-medium text-navy">
              Yêu cầu tạm ngừng đang chờ duyệt:
              <strong class="ml-1 font-bold text-amber tabular-nums">{{ overview.pendingAvailabilityRequests }}</strong>
            </span>
            <div class="flex items-center gap-3">
              <RouterLink :to="{ name: 'admin-availability' }" class="font-semibold text-teal hover:underline">
                Xử lý tạm ngừng
              </RouterLink>
              <RouterLink :to="{ name: 'admin-assignment-config' }" class="font-semibold text-navy hover:underline">
                Cấu hình phân công
              </RouterLink>
            </div>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>
