<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { CalendarOff, Plus, RefreshCw, XCircle } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'
import {
  cancelMyAvailabilityRequest,
  createMyAvailabilityRequest,
  extractApiError,
  fetchMyAvailabilityRequests,
} from '@/service/expertPhase3ApiService'

const STATUS_META = {
  PENDING: { label: 'Chờ ADMIN duyệt', tone: 'warning' },
  APPROVED: { label: 'Đã phê duyệt', tone: 'teal' },
  REJECTED: { label: 'Bị từ chối', tone: 'danger' },
  CANCELLED: { label: 'Đã hủy / Thu hồi', tone: 'neutral' },
  COMPLETED: { label: 'Đã kết thúc', tone: 'success' },
  EXPIRED: { label: 'Hết hạn duyệt', tone: 'neutral' },
}

const loading = ref(true)
const error = ref('')
const feedback = ref('')
const items = ref([])
const submitting = ref(false)

const form = reactive({
  ngayBatDau: '',
  ngayKetThuc: '',
  lyDo: '',
})

const cancelOpen = ref(false)
const cancelTarget = ref(null)
const cancelReason = ref('')
const cancelBusy = ref(false)
const cancelError = ref('')

const activeApproved = computed(() => {
  const now = Date.now()
  return items.value.find((req) => {
    if (req.trangThai !== 'APPROVED') return false
    const start = new Date(`${req.ngayBatDau}Z`).getTime()
    const end = new Date(`${req.ngayKetThuc}Z`).getTime()
    return now >= start && now < end
  })
})

function canCancel(req) {
  if (req.trangThai === 'PENDING') return true
  if (req.trangThai === 'APPROVED') {
    return Date.now() < new Date(`${req.ngayBatDau}Z`).getTime()
  }
  return false
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    items.value = await fetchMyAvailabilityRequests({ limit: 50 })
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải lịch sử yêu cầu tạm ngừng.')
  } finally {
    loading.value = false
  }
}

async function submitRequest() {
  error.value = ''
  feedback.value = ''
  if (!form.ngayBatDau || !form.ngayKetThuc) {
    error.value = 'Vui lòng chọn đầy đủ thời điểm bắt đầu và kết thúc.'
    return
  }
  const startDt = new Date(form.ngayBatDau)
  const endDt = new Date(form.ngayKetThuc)
  if (endDt <= startDt) {
    error.value = 'Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu.'
    return
  }
  if (form.lyDo.trim().length < 5) {
    error.value = 'Vui lòng nhập lý do tạm ngừng tối thiểu 5 ký tự.'
    return
  }
  submitting.value = true
  try {
    await createMyAvailabilityRequest({
      ngayBatDau: startDt.toISOString(),
      ngayKetThuc: endDt.toISOString(),
      lyDo: form.lyDo.trim(),
    })
    form.ngayBatDau = ''
    form.ngayKetThuc = ''
    form.lyDo = ''
    feedback.value = 'Đã gửi yêu cầu tạm ngừng nhận nhiệm vụ thành công. Vui lòng chờ Quản trị viên phê duyệt.'
    await loadData()
  } catch (err) {
    error.value = extractApiError(err, 'Không thể gửi yêu cầu tạm ngừng.')
  } finally {
    submitting.value = false
  }
}

function openCancel(req) {
  cancelTarget.value = req
  cancelReason.value = ''
  cancelError.value = ''
  cancelOpen.value = true
}

async function confirmCancel() {
  if (cancelReason.value.trim().length < 5) {
    cancelError.value = 'Vui lòng nhập lý do hủy tối thiểu 5 ký tự.'
    return
  }
  cancelBusy.value = true
  cancelError.value = ''
  try {
    await cancelMyAvailabilityRequest(cancelTarget.value.maYeuCau, cancelReason.value.trim())
    cancelOpen.value = false
    feedback.value = `Đã hủy yêu cầu tạm ngừng #${cancelTarget.value.maYeuCau}.`
    await loadData()
  } catch (err) {
    cancelError.value = extractApiError(err, 'Không thể hủy yêu cầu tạm ngừng.')
  } finally {
    cancelBusy.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Lịch làm việc cá nhân</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Tạm ngừng nhận nhiệm vụ</h1>
        <p class="mt-1 text-sm text-muted">
          Đăng ký khoảng thời gian tạm nghỉ để hệ thống tạm dừng phân công nhiệm vụ mới cho bạn.
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

    <UiAlert
      variant="info"
      title="Quy định tạm ngừng nhận nhiệm vụ"
      message="Yêu cầu tạm ngừng tối đa 30 ngày (theo cấu hình hệ thống) và cần Quản trị viên phê duyệt. Trong thời gian được duyệt, bạn không nhận thêm nhiệm vụ mới nhưng vẫn phải hoàn thành các nhiệm vụ đã được giao trước đó; hệ thống không tự động gia hạn deadline hay miễn trừ vi phạm."
    />

    <UiAlert
      v-if="activeApproved"
      variant="success"
      title="Bạn đang trong đợt tạm ngừng đã được phê duyệt"
      :message="`Thời điểm dự kiến nhận nhiệm vụ trở lại: ${formatDateTimeVi(activeApproved.ngayKetThuc)}.`"
    />

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Request Form -->
    <form class="rounded-xl border border-border bg-surface p-5 space-y-4" @submit.prevent="submitRequest">
      <div class="flex items-center gap-2 border-b border-border/70 pb-3">
        <Plus :size="16" class="text-teal" aria-hidden="true" />
        <h2 class="text-sm font-bold text-navy">Gửi yêu cầu tạm ngừng mới</h2>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label class="block text-xs font-semibold text-navy">
          Thời điểm bắt đầu <span class="text-danger">*</span>
          <input v-model="form.ngayBatDau" type="datetime-local" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none" />
        </label>
        <label class="block text-xs font-semibold text-navy">
          Thời điểm kết thúc <span class="text-danger">*</span>
          <input v-model="form.ngayKetThuc" type="datetime-local" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none" />
        </label>
      </div>

      <label class="block text-xs font-semibold text-navy">
        Lý do tạm ngừng <span class="text-danger">*</span>
        <textarea v-model="form.lyDo" rows="2" required placeholder="Nhập lý do cụ thể (tối thiểu 5 ký tự)..." class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none" />
      </label>

      <div class="flex justify-end">
        <button
          type="submit"
          class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-4 py-2 text-xs font-semibold text-white hover:bg-navy/90 disabled:opacity-50"
          :disabled="submitting"
        >
          <CalendarOff :size="14" aria-hidden="true" />
          <span>{{ submitting ? 'Đang gửi...' : 'Gửi yêu cầu tạm ngừng' }}</span>
        </button>
      </div>
    </form>

    <!-- History Table -->
    <UiSkeleton v-if="loading" variant="table" :lines="5" />

    <UiEmptyState
      v-else-if="items.length === 0"
      :icon="CalendarOff"
      title="Chưa có yêu cầu tạm ngừng nào"
      description="Lịch sử đăng ký tạm ngừng và phản hồi từ Quản trị viên sẽ hiển thị tại đây."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-left text-xs">
        <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
          <tr>
            <th class="px-4 py-3">Mã</th>
            <th class="px-4 py-3">Khoảng thời gian</th>
            <th class="px-4 py-3">Lý do</th>
            <th class="px-4 py-3">Trạng thái</th>
            <th class="px-4 py-3">Phản hồi ADMIN</th>
            <th class="px-4 py-3 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/70">
          <tr v-for="req in items" :key="req.maYeuCau" class="hover:bg-subtle/40">
            <td class="px-4 py-3 font-mono font-bold text-navy">#{{ req.maYeuCau }}</td>
            <td class="px-4 py-3 tabular-nums">
              <p class="font-medium text-navy">{{ formatDateTimeVi(req.ngayBatDau) }}</p>
              <p class="text-muted">→ {{ formatDateTimeVi(req.ngayKetThuc) }}</p>
            </td>
            <td class="px-4 py-3 max-w-xs text-slate-700">{{ req.lyDo }}</td>
            <td class="px-4 py-3">
              <UiStatusBadge
                :tone="STATUS_META[req.trangThai]?.tone || 'neutral'"
                :label="STATUS_META[req.trangThai]?.label || req.trangThai"
              />
            </td>
            <td class="px-4 py-3 max-w-xs text-muted">
              <p v-if="req.ghiChuXuLy">{{ req.ghiChuXuLy }}</p>
              <p v-if="req.lyDoHuy" class="text-danger">Hủy: {{ req.lyDoHuy }}</p>
              <span v-if="!req.ghiChuXuLy && !req.lyDoHuy">—</span>
            </td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="canCancel(req)"
                type="button"
                class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                @click="openCancel(req)"
              >
                <XCircle :size="13" aria-hidden="true" />
                <span>Hủy yêu cầu</span>
              </button>
              <span v-else class="text-[11px] text-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Cancel Modal -->
    <div v-if="cancelOpen && cancelTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Hủy yêu cầu tạm ngừng">
        <h2 class="text-base font-bold text-navy">Hủy yêu cầu tạm ngừng #{{ cancelTarget.maYeuCau }}</h2>
        <UiAlert v-if="cancelError" class="mt-3" variant="danger" :message="cancelError" />
        <label class="mt-4 block text-xs font-semibold text-navy">
          Lý do hủy <span class="text-danger">*</span>
          <textarea v-model="cancelReason" rows="3" placeholder="Nhập lý do hủy tối thiểu 5 ký tự..." class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none" />
        </label>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle" :disabled="cancelBusy" @click="cancelOpen = false">
            Đóng
          </button>
          <button type="button" class="rounded-lg bg-danger px-4 py-2 text-xs font-semibold text-white hover:bg-danger/90 disabled:opacity-50" :disabled="cancelBusy" @click="confirmCancel">
            {{ cancelBusy ? 'Đang hủy...' : 'Xác nhận hủy' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
