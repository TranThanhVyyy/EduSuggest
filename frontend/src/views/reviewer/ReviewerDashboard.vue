<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangle,
  Bell,
  CalendarOff,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  RefreshCw,
  ShieldAlert,
  UserCheck,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatCard from '@/components/ui/UiStatCard.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'
import {
  extractApiError,
  fetchMyAccountabilitySummary,
  fetchMyAssignments,
  fetchMyAvailabilityRequests,
  fetchMyExpertProfile,
  formatRemainingTime,
} from '@/service/expertPhase3ApiService'
import { fetchUnreadNotificationCount } from '@/service/notificationApiService'

const loading = ref(true)
const error = ref('')
const profile = ref(null)
const assignments = ref([])
const accountability = ref(null)
const availabilityList = ref([])
const unreadCount = ref(0)

const isVerified = computed(() => (profile.value?.trangThaiHoSo || '').toUpperCase() === 'VERIFIED')
const needsPasswordChange = computed(() => Boolean(profile.value?.batBuocDoiMatKhau))

const counts = computed(() => {
  const list = assignments.value
  return {
    assigned: list.filter((a) => a.trangThai === 'ASSIGNED').length,
    accepted: list.filter((a) => a.trangThai === 'ACCEPTED').length,
    inProgress: list.filter((a) => a.trangThai === 'IN_PROGRESS').length,
    completed: list.filter((a) => a.trangThai === 'COMPLETED').length,
    overdue: list.filter((a) => a.isOverdueReview).length,
    activeLoad: list.filter((a) => ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(a.trangThai)).length,
  }
})

const urgentTasks = computed(() => {
  return assignments.value
    .filter((a) => ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(a.trangThai))
    .slice(0, 6)
})

const activePause = computed(() => {
  const now = Date.now()
  return availabilityList.value.find((req) => {
    if (req.trangThai !== 'APPROVED') return false
    const start = new Date(`${req.ngayBatDau}Z`).getTime()
    const end = new Date(`${req.ngayKetThuc}Z`).getTime()
    return now >= start && now < end
  })
})

const DISCIPLINE_META = {
  NORMAL: { label: 'Bình thường', tone: 'success' },
  WARNING: { label: 'Cảnh báo', tone: 'warning' },
  FINAL_WARNING: { label: 'Cảnh báo cuối', tone: 'amber' },
  LOCKED: { label: 'Đã khóa', tone: 'danger' },
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [profRes, accRes, notifRes] = await Promise.allSettled([
      fetchMyExpertProfile(),
      fetchMyAccountabilitySummary(),
      fetchUnreadNotificationCount(),
    ])
    if (profRes.status === 'fulfilled') profile.value = profRes.value
    if (accRes.status === 'fulfilled') accountability.value = accRes.value
    if (notifRes.status === 'fulfilled') unreadCount.value = notifRes.value

    if ((profile.value?.trangThaiHoSo || '').toUpperCase() === 'VERIFIED' && !profile.value?.batBuocDoiMatKhau) {
      const [assignRes, availRes] = await Promise.allSettled([
        fetchMyAssignments({ limit: 50 }),
        fetchMyAvailabilityRequests({ limit: 20 }),
      ])
      if (assignRes.status === 'fulfilled') assignments.value = Array.isArray(assignRes.value) ? assignRes.value : []
      if (availRes.status === 'fulfilled') availabilityList.value = Array.isArray(availRes.value) ? availRes.value : []
    }
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải dữ liệu bảng điều khiển chuyên gia.')
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
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Không gian chuyên gia</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Tổng quan kiểm duyệt</h1>
        <p class="mt-1 text-sm text-muted">
          Theo dõi nhiệm vụ được phân công, tải công việc, tình trạng kỷ luật và thông báo hệ thống.
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

    <div v-if="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UiSkeleton v-for="i in 8" :key="i" variant="rect" height="112px" rounded="12px" />
    </div>

    <!-- Unverified / Onboarding Gate -->
    <template v-else-if="!isVerified || needsPasswordChange">
      <UiAlert
        variant="warning"
        title="Hồ sơ chuyên gia chưa sẵn sàng nhận nhiệm vụ"
        :message="
          needsPasswordChange
            ? 'Bạn cần đổi mật khẩu tạm và hoàn thiện hồ sơ chuyên môn trước khi gửi Quản trị viên xác minh.'
            : `Trạng thái hồ sơ hiện tại: ${profile?.trangThaiHoSo || 'CHƯA XÁC MINH'}. Hệ thống chỉ phân công kiểm duyệt sau khi Quản trị viên xác minh hồ sơ (VERIFIED).`
        "
      />
      <div class="rounded-xl border border-border bg-surface p-6 flex flex-wrap items-center justify-between gap-4">
        <div class="space-y-1">
          <h2 class="text-base font-bold text-navy">Hoàn thiện hồ sơ & chuyên môn</h2>
          <p class="text-sm text-muted">
            Cập nhật thông tin kinh nghiệm, chọn chuyên môn chính/phụ và gửi hồ sơ chờ ADMIN xác minh.
          </p>
        </div>
        <RouterLink
          :to="{ name: 'reviewer-profile' }"
          class="inline-flex items-center gap-2 rounded-lg bg-navy px-4 py-2.5 text-xs font-semibold text-white hover:bg-navy/90"
        >
          <UserCheck :size="15" aria-hidden="true" />
          <span>Đi tới hồ sơ chuyên gia</span>
        </RouterLink>
      </div>
    </template>

    <!-- Verified Expert Dashboard -->
    <template v-else>
      <UiAlert
        v-if="activePause"
        variant="info"
        title="Bạn đang trong khoảng thời gian tạm ngừng nhận nhiệm vụ mới"
        :message="`Hiệu lực đến ${formatDateTimeVi(activePause.ngayKetThuc)}. Các nhiệm vụ đã được giao trước đó vẫn cần hoàn thành đúng hạn.`"
      />

      <!-- KPI Bento Grid -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <UiStatCard
          title="Chờ tiếp nhận"
          :value="counts.assigned"
          description="Nhiệm vụ mới cần phản hồi trước hạn"
          :icon="Clock"
          variant="amber"
          size="sm"
        />
        <UiStatCard
          title="Đã tiếp nhận / Đang duyệt"
          :value="counts.accepted + counts.inProgress"
          :description="`${counts.accepted} đã nhận · ${counts.inProgress} đang kiểm duyệt`"
          :icon="ClipboardCheck"
          variant="teal"
          size="sm"
        />
        <UiStatCard
          title="Đã hoàn thành"
          :value="counts.completed"
          description="Nhiệm vụ đã gửi quyết định"
          :icon="CheckCircle2"
          size="sm"
        />
        <UiStatCard
          title="Quá hạn kiểm duyệt"
          :value="counts.overdue"
          description="Cần xử lý ưu tiên ngay"
          :icon="AlertTriangle"
          :variant="counts.overdue > 0 ? 'amber' : 'default'"
          size="sm"
        />
        <UiStatCard
          title="Tải công việc mở"
          :value="counts.activeLoad"
          description="Nhiệm vụ đang mở hiện tại"
          :icon="ClipboardCheck"
          variant="primary"
          size="sm"
        />
        <UiStatCard
          title="Vi phạm (168 giờ)"
          :value="accountability ? `${accountability.confirmedViolationsInWindow}/${accountability.lockThreshold}` : '0'"
          :description="accountability ? `Còn ${accountability.remainingBeforeLock} lần trước ngưỡng khóa` : 'Cửa sổ 7 ngày liên tục'"
          :icon="ShieldAlert"
          size="sm"
        />
        <UiStatCard
          title="Trạng thái tạm ngừng"
          :value="activePause ? 'Đang tạm ngừng' : 'Sẵn sàng'"
          :description="activePause ? `Đến ${formatDateTimeVi(activePause.ngayKetThuc)}` : 'Đủ điều kiện nhận nhiệm vụ mới'"
          :icon="CalendarOff"
          size="sm"
        />
        <UiStatCard
          title="Thông báo chưa đọc"
          :value="unreadCount"
          description="Cảnh báo phân công & kỷ luật"
          :icon="Bell"
          size="sm"
        />
      </div>

      <!-- Status Summary Strip -->
      <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface px-5 py-3.5 text-xs">
        <div class="flex flex-wrap items-center gap-3">
          <span class="font-semibold text-navy">Hồ sơ:</span>
          <UiStatusBadge tone="success" label="VERIFIED" />
          <span class="font-semibold text-navy ml-2">Mức kỷ luật:</span>
          <UiStatusBadge
            :tone="DISCIPLINE_META[accountability?.disciplineLevel]?.tone || 'success'"
            :label="DISCIPLINE_META[accountability?.disciplineLevel]?.label || 'Bình thường'"
          />
          <span v-if="accountability" class="text-muted">Chu kỳ #{{ accountability.currentCycle }}</span>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <RouterLink :to="{ name: 'reviewer-accountability' }" class="font-semibold text-teal hover:underline">Xem kỷ luật</RouterLink>
          <RouterLink :to="{ name: 'reviewer-availability' }" class="font-semibold text-navy hover:underline">Đăng ký tạm ngừng</RouterLink>
        </div>
      </div>

      <!-- Urgent Tasks -->
      <section class="rounded-xl border border-border bg-surface p-5 space-y-4">
        <div class="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
          <div>
            <h2 class="text-sm font-bold text-navy">Nhiệm vụ cần xử lý sớm</h2>
            <p class="text-xs text-muted">Danh sách nhiệm vụ được hệ thống phân công trực tiếp cho bạn</p>
          </div>
          <RouterLink :to="{ name: 'reviewer-assignments' }" class="text-xs font-semibold text-teal hover:underline">
            Xem tất cả nhiệm vụ
          </RouterLink>
        </div>

        <UiEmptyState
          v-if="urgentTasks.length === 0"
          title="Hiện chưa có nhiệm vụ đang mở"
          description="Khi hệ thống phân công khóa học hoặc tài liệu phù hợp chuyên môn, nhiệm vụ sẽ xuất hiện tại đây."
        />

        <div v-else class="divide-y divide-border/70">
          <div
            v-for="task in urgentTasks"
            :key="task.maPhanCong"
            class="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded bg-subtle px-1.5 py-0.5 font-mono text-[10px] font-semibold text-navy">
                  {{ task.loaiDoiTuong }} #{{ task.maDoiTuong }}
                </span>
                <UiStatusBadge
                  :tone="task.trangThai === 'ASSIGNED' ? 'warning' : task.trangThai === 'IN_PROGRESS' ? 'teal' : 'info'"
                  :label="task.trangThai"
                />
                <span class="text-[11px] font-medium text-amber-dark tabular-nums">
                  {{ task.trangThai === 'ASSIGNED' ? formatRemainingTime(task.hanTiepNhan) : formatRemainingTime(task.hanKiemDuyet) }}
                </span>
              </div>
              <p class="mt-1 truncate text-sm font-semibold text-navy">
                {{ task.tieuDeDoiTuong || `Nội dung #${task.maDoiTuong}` }}
              </p>
            </div>

            <RouterLink
              :to="{ name: 'reviewer-assignment-detail', params: { assignmentId: String(task.maPhanCong) } }"
              class="shrink-0 rounded-lg bg-navy px-3 py-1.5 text-center text-xs font-semibold text-white hover:bg-navy/90"
            >
              {{ task.trangThai === 'ASSIGNED' ? 'Xem & Tiếp nhận' : 'Mở không gian duyệt' }}
            </RouterLink>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>
