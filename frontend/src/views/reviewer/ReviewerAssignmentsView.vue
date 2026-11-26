<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'
import {
  DECLINE_REASON_OPTIONS,
  acceptMyAssignment,
  declineMyAssignment,
  extractApiError,
  fetchMyAssignments,
  formatRemainingTime,
} from '@/service/expertPhase3ApiService'

const props = defineProps({
  defaultTargetType: {
    type: String,
    default: '',
  },
})

const router = useRouter()
const loading = ref(true)
const error = ref('')
const feedback = ref('')
const items = ref([])
const statusFilter = ref('')
const targetTypeFilter = ref(props.defaultTargetType || '')
const searchQuery = ref('')
const limit = 20
const offset = ref(0)
const nowTick = ref(Date.now())
const busyId = ref(null)

// Decline modal
const declineOpen = ref(false)
const declineTarget = ref(null)
const declineCode = ref('WORKLOAD_PERSONAL')
const declineReason = ref('')
const declineBusy = ref(false)
const declineError = ref('')

const STATUS_META = {
  ASSIGNED: { label: 'Chờ tiếp nhận', tone: 'warning' },
  ACCEPTED: { label: 'Đã tiếp nhận', tone: 'info' },
  IN_PROGRESS: { label: 'Đang kiểm duyệt', tone: 'teal' },
  COMPLETED: { label: 'Hoàn thành', tone: 'success' },
  DECLINED: { label: 'Đã từ chối', tone: 'danger' },
  EXPIRED: { label: 'Hết hạn tiếp nhận', tone: 'danger' },
  CANCELLED: { label: 'Đã thu hồi', tone: 'neutral' },
}

const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase('vi')
  if (!q) return items.value
  return items.value.filter((item) => {
    const hay = [String(item.maPhanCong), item.tieuDeDoiTuong || '', item.loaiDoiTuong || '', item.lyDoPhanCong || '']
      .join(' ')
      .toLocaleLowerCase('vi')
    return hay.includes(q)
  })
})

const selectedDeclineOption = computed(() =>
  DECLINE_REASON_OPTIONS.find((o) => o.code === declineCode.value),
)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchMyAssignments({
      status: statusFilter.value,
      targetType: targetTypeFilter.value,
      limit,
      offset: offset.value,
    })
    items.value = Array.isArray(res) ? res : []
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải danh sách nhiệm vụ được phân công.')
  } finally {
    loading.value = false
  }
}

async function handleAccept(item) {
  if (busyId.value) return
  busyId.value = item.maPhanCong
  error.value = ''
  feedback.value = ''
  try {
    await acceptMyAssignment(item.maPhanCong)
    feedback.value = `Đã tiếp nhận nhiệm vụ #${item.maPhanCong}. Bạn có thể bắt đầu kiểm duyệt ngay.`
    await loadData()
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tiếp nhận nhiệm vụ.')
  } finally {
    busyId.value = null
  }
}

function openDecline(item) {
  declineTarget.value = item
  declineCode.value = 'WORKLOAD_PERSONAL'
  declineReason.value = ''
  declineError.value = ''
  declineOpen.value = true
}

async function submitDecline() {
  if (!declineTarget.value) return
  if (declineReason.value.trim().length < 5) {
    declineError.value = 'Vui lòng giải thích lý do từ chối tối thiểu 5 ký tự.'
    return
  }
  declineBusy.value = true
  declineError.value = ''
  try {
    await declineMyAssignment(declineTarget.value.maPhanCong, {
      maLyDoTuChoi: declineCode.value,
      lyDoTuChoi: declineReason.value.trim(),
    })
    declineOpen.value = false
    feedback.value = `Đã từ chối nhiệm vụ #${declineTarget.value.maPhanCong}. Hệ thống sẽ tự động phân công lại.`
    await loadData()
  } catch (err) {
    declineError.value = extractApiError(err, 'Không thể từ chối nhiệm vụ.')
  } finally {
    declineBusy.value = false
  }
}

function openWorkspace(item) {
  router.push({ name: 'reviewer-assignment-detail', params: { assignmentId: String(item.maPhanCong) } })
}

let timer = null
onMounted(() => {
  loadData()
  timer = window.setInterval(() => {
    nowTick.value = Date.now()
  }, 30000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})

watch([statusFilter, targetTypeFilter], () => {
  offset.value = 0
  loadData()
})
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Phân công cá nhân</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Nhiệm vụ kiểm duyệt của tôi</h1>
        <p class="mt-1 text-sm text-muted">
          Chỉ hiển thị các khóa học và tài liệu được hệ thống phân công trực tiếp cho bạn (không lấy từ kho tự chọn).
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white hover:bg-navy/90"
        :disabled="loading"
        @click="loadData"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Filters -->
    <div class="grid grid-cols-1 gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-3">
      <label class="relative block">
        <span class="sr-only">Tìm kiếm nhiệm vụ</span>
        <Search :size="15" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Tìm theo tiêu đề, mã phân công..."
          class="w-full rounded-lg border border-border bg-canvas py-2 pl-9 pr-3 text-xs text-ink focus:border-teal focus:outline-none"
        />
      </label>

      <select
        v-model="statusFilter"
        aria-label="Lọc trạng thái nhiệm vụ"
        class="rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả trạng thái</option>
        <option v-for="(meta, key) in STATUS_META" :key="key" :value="key">{{ meta.label }} ({{ key }})</option>
      </select>

      <select
        v-model="targetTypeFilter"
        aria-label="Lọc loại nội dung"
        class="rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả loại nội dung</option>
        <option value="COURSE">Khóa học (COURSE)</option>
        <option value="MATERIAL">Tài liệu độc lập (MATERIAL)</option>
      </select>
    </div>

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <UiEmptyState
      v-else-if="filteredItems.length === 0"
      title="Chưa có nhiệm vụ phân công phù hợp"
      description="Bạn hiện không có nhiệm vụ nào khớp bộ lọc. Hệ thống sẽ gửi thông báo ngay khi có phân công mới."
    />

    <div v-else class="space-y-3">
      <article
        v-for="item in filteredItems"
        :key="item.maPhanCong"
        class="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-slate-300"
      >
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-0 flex-1 space-y-1.5">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded bg-subtle px-1.5 py-0.5 font-mono text-[11px] font-semibold text-navy">
                {{ item.loaiDoiTuong === 'COURSE' ? 'Khóa học' : 'Tài liệu' }} #{{ item.maDoiTuong }}
              </span>
              <span class="font-mono text-[11px] text-muted">PC#{{ item.maPhanCong }} · Vòng {{ item.soVongKiemDuyet }}</span>
              <UiStatusBadge
                :tone="STATUS_META[item.trangThai]?.tone || 'neutral'"
                :label="STATUS_META[item.trangThai]?.label || item.trangThai"
              />
              <span v-if="item.diemPhuHop !== null && item.diemPhuHop !== undefined" class="font-mono text-[11px] font-semibold text-teal">
                {{ Number(item.diemPhuHop).toFixed(2) }} điểm
              </span>
            </div>

            <h2 class="text-base font-bold text-navy">
              {{ item.tieuDeDoiTuong || `Nội dung #${item.maDoiTuong}` }}
            </h2>

            <p v-if="item.lyDoPhanCong" class="text-xs text-slate-600">{{ item.lyDoPhanCong }}</p>

            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted tabular-nums">
              <span>Giao lúc: {{ formatDateTimeVi(item.ngayPhanCong) }}</span>
              <span class="inline-flex items-center gap-1 font-medium text-navy">
                <Clock :size="12" class="text-amber" aria-hidden="true" />
                Hạn tiếp nhận: {{ formatDateTimeVi(item.hanTiepNhan) }}
                <strong v-if="item.trangThai === 'ASSIGNED'" class="text-amber-dark">
                  ({{ formatRemainingTime(item.hanTiepNhan, nowTick) }})
                </strong>
              </span>
              <span v-if="item.hanKiemDuyet">
                Hạn duyệt: {{ formatDateTimeVi(item.hanKiemDuyet) }}
              </span>
              <span v-if="item.isOverdueReview" class="inline-flex items-center gap-1 font-semibold text-danger">
                <AlertTriangle :size="12" aria-hidden="true" />
                Quá hạn kiểm duyệt
              </span>
            </div>
          </div>

          <!-- Actions strictly driven by Backend allowedActions -->
          <div class="flex shrink-0 flex-wrap items-center gap-2">
            <button
              v-if="item.allowedActions?.includes('accept')"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg bg-teal px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50"
              :disabled="busyId === item.maPhanCong"
              @click="handleAccept(item)"
            >
              <CheckCircle2 :size="14" aria-hidden="true" />
              <span>{{ busyId === item.maPhanCong ? 'Đang tiếp nhận...' : 'Tiếp nhận' }}</span>
            </button>

            <button
              v-if="item.allowedActions?.includes('decline')"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs font-semibold text-danger hover:bg-danger/10"
              @click="openDecline(item)"
            >
              <XCircle :size="14" aria-hidden="true" />
              <span>Từ chối</span>
            </button>

            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy hover:bg-subtle"
              @click="openWorkspace(item)"
            >
              <ExternalLink :size="14" aria-hidden="true" />
              <span>{{ ['ACCEPTED', 'IN_PROGRESS'].includes(item.trangThai) ? 'Không gian kiểm duyệt' : 'Xem chi tiết' }}</span>
            </button>
          </div>
        </div>
      </article>
    </div>

    <div class="flex items-center justify-between">
      <p class="text-xs text-muted tabular-nums">Hiển thị {{ filteredItems.length }} nhiệm vụ (offset {{ offset }})</p>
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
          :disabled="items.length < limit"
          @click="offset += limit; loadData()"
        >
          <span>Sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </div>
    </div>

    <!-- Decline Modal with Policy Warning -->
    <div v-if="declineOpen && declineTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Từ chối nhiệm vụ kiểm duyệt">
        <h2 class="text-base font-bold text-navy">Từ chối nhiệm vụ #{{ declineTarget.maPhanCong }}</h2>

        <UiAlert
          class="mt-3"
          :variant="selectedDeclineOption?.autoViolation ? 'warning' : 'info'"
          :title="selectedDeclineOption?.autoViolation ? 'Cảnh báo chính sách kỷ luật' : 'Lưu ý quy trình xác minh lý do'"
          :message="
            selectedDeclineOption?.autoViolation
              ? 'Lý do bận cá nhân / quá tải được tính là 1 vi phạm CONFIRMED trong cửa sổ 168 giờ (đạt 4 vi phạm sẽ tự động khóa tài khoản).'
              : 'Lý do này sẽ được ghi nhận ở trạng thái PENDING_REVIEW để Quản trị viên xác minh hoặc miễn trừ; hệ thống không tự động miễn trừ.'
          "
        />

        <UiAlert v-if="declineError" class="mt-3" variant="danger" :message="declineError" />

        <div class="mt-4 space-y-3">
          <label class="block text-xs font-semibold text-navy">
            Mã lý do từ chối <span class="text-danger">*</span>
            <select
              v-model="declineCode"
              class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
            >
              <option v-for="opt in DECLINE_REASON_OPTIONS" :key="opt.code" :value="opt.code">
                {{ opt.label }}
              </option>
            </select>
          </label>

          <label class="block text-xs font-semibold text-navy">
            Giải thích chi tiết <span class="text-danger">*</span>
            <textarea
              v-model="declineReason"
              rows="3"
              placeholder="Mô tả rõ lý do từ chối (tối thiểu 5 ký tự)..."
              class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none"
            />
          </label>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle" :disabled="declineBusy" @click="declineOpen = false">
            Hủy bỏ
          </button>
          <button type="button" class="rounded-lg bg-danger px-4 py-2 text-xs font-semibold text-white hover:bg-danger/90 disabled:opacity-50" :disabled="declineBusy" @click="submitDecline">
            {{ declineBusy ? 'Đang gửi...' : 'Xác nhận từ chối' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
