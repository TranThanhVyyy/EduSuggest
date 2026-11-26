<script setup>
import { onMounted, ref, watch } from 'vue'
import { CalendarOff, CheckCircle2, RefreshCw, XCircle } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  approveAvailabilityRequest,
  extractApiError,
  fetchAdminAvailabilityRequests,
  formatDateTimeVi,
  rejectAvailabilityRequest,
  revokeAvailabilityRequest,
} from '@/service/adminPhase3ApiService'

const STATUS_META = {
  PENDING: { label: 'Chờ duyệt', tone: 'warning' },
  APPROVED: { label: 'Đã phê duyệt', tone: 'teal' },
  REJECTED: { label: 'Đã từ chối', tone: 'danger' },
  CANCELLED: { label: 'Đã hủy / Thu hồi', tone: 'neutral' },
  COMPLETED: { label: 'Đã kết thúc', tone: 'success' },
  EXPIRED: { label: 'Hết hạn duyệt', tone: 'neutral' },
}

const loading = ref(true)
const error = ref('')
const feedback = ref('')
const items = ref([])
const statusFilter = ref('')
const activeNowOnly = ref(false)

const modalOpen = ref(false)
const modalType = ref('') // 'approve' | 'reject' | 'revoke'
const modalTarget = ref(null)
const modalNote = ref('')
const modalBusy = ref(false)
const modalError = ref('')

function durationDays(req) {
  const start = new Date(`${req.ngayBatDau}Z`)
  const end = new Date(`${req.ngayKetThuc}Z`)
  const diff = (end - start) / (1000 * 60 * 60 * 24)
  if (!Number.isFinite(diff) || diff <= 0) return '—'
  return `${Math.round(diff * 10) / 10} ngày`
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    items.value = await fetchAdminAvailabilityRequests({
      status: activeNowOnly.value ? '' : statusFilter.value,
      activeNow: activeNowOnly.value,
      limit: 50,
    })
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải danh sách yêu cầu tạm ngừng.')
  } finally {
    loading.value = false
  }
}

function openModal(type, item) {
  modalType.value = type
  modalTarget.value = item
  modalNote.value = ''
  modalError.value = ''
  modalOpen.value = true
}

async function submitModal() {
  if ((modalType.value === 'reject' || modalType.value === 'revoke') && modalNote.value.trim().length < 5) {
    modalError.value = 'Bắt buộc nhập lý do tối thiểu 5 ký tự.'
    return
  }
  modalBusy.value = true
  modalError.value = ''
  try {
    const id = modalTarget.value.maYeuCau
    if (modalType.value === 'approve') {
      await approveAvailabilityRequest(id, modalNote.value)
      feedback.value = `Đã phê duyệt yêu cầu tạm ngừng #${id}.`
    } else if (modalType.value === 'reject') {
      await rejectAvailabilityRequest(id, modalNote.value.trim())
      feedback.value = `Đã từ chối yêu cầu tạm ngừng #${id}.`
    } else {
      await revokeAvailabilityRequest(id, modalNote.value.trim())
      feedback.value = `Đã thu hồi lịch tạm ngừng #${id} và đánh thức hàng đợi chờ phân công.`
    }
    modalOpen.value = false
    await loadData()
  } catch (err) {
    modalError.value = extractApiError(err, 'Không thể xử lý yêu cầu tạm ngừng.')
  } finally {
    modalBusy.value = false
  }
}

watch([statusFilter, activeNowOnly], loadData)
onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Trạng thái sẵn sàng</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Quản lý yêu cầu tạm ngừng nhận nhiệm vụ</h1>
        <p class="mt-1 text-sm text-muted">
          Phê duyệt, từ chối hoặc thu hồi lịch tạm ngừng của chuyên gia. Phê duyệt tạm ngừng không tự động hủy các nhiệm vụ đã giao trước đó.
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
    <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface p-3.5">
      <div class="flex flex-wrap items-center gap-2">
        <select
          v-model="statusFilter"
          :disabled="activeNowOnly"
          aria-label="Lọc trạng thái yêu cầu tạm ngừng"
          class="rounded-lg border border-border bg-canvas px-3 py-1.5 text-xs text-ink focus:border-teal focus:outline-none disabled:opacity-50"
        >
          <option value="">Tất cả trạng thái</option>
          <option v-for="(meta, key) in STATUS_META" :key="key" :value="key">{{ meta.label }} ({{ key }})</option>
        </select>

        <label class="inline-flex items-center gap-2 rounded-lg border border-border bg-canvas px-3 py-1.5 text-xs font-medium text-navy">
          <input v-model="activeNowOnly" type="checkbox" class="size-3.5 rounded border-border text-teal focus:ring-teal" />
          <span>Chỉ chuyên gia đang tạm ngừng hiện tại</span>
        </label>
      </div>
      <p class="text-xs text-muted tabular-nums">{{ items.length }} yêu cầu</p>
    </div>

    <UiSkeleton v-if="loading" variant="table" :lines="5" />

    <UiEmptyState
      v-else-if="items.length === 0"
      :icon="CalendarOff"
      title="Chưa có yêu cầu tạm ngừng phù hợp"
      description="Các yêu cầu tạm ngừng do chuyên gia gửi lên sẽ hiển thị tại đây."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-left text-xs">
        <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
          <tr>
            <th class="px-4 py-3">Yêu cầu / Chuyên gia</th>
            <th class="px-4 py-3">Khoảng thời gian</th>
            <th class="px-4 py-3">Lý do</th>
            <th class="px-4 py-3">Trạng thái</th>
            <th class="px-4 py-3">Ghi chú xử lý</th>
            <th class="px-4 py-3 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/70">
          <tr v-for="req in items" :key="req.maYeuCau" class="hover:bg-subtle/40">
            <td class="px-4 py-3">
              <p class="font-mono font-bold text-navy">#{{ req.maYeuCau }}</p>
              <p class="text-[11px] text-muted">Chuyên gia #{{ req.maChuyenGia }}</p>
            </td>
            <td class="px-4 py-3 tabular-nums">
              <p class="font-medium text-navy">{{ formatDateTimeVi(req.ngayBatDau) }}</p>
              <p class="text-muted">→ {{ formatDateTimeVi(req.ngayKetThuc) }} ({{ durationDays(req) }})</p>
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
              <p v-if="req.lyDoHuy" class="text-danger">Hủy/Thu hồi: {{ req.lyDoHuy }}</p>
              <span v-if="!req.ghiChuXuLy && !req.lyDoHuy">—</span>
            </td>
            <td class="px-4 py-3 text-right">
              <div v-if="req.trangThai === 'PENDING'" class="inline-flex items-center gap-1.5">
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg bg-teal px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-teal-dark"
                  @click="openModal('approve', req)"
                >
                  <CheckCircle2 :size="13" aria-hidden="true" />
                  <span>Phê duyệt</span>
                </button>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                  @click="openModal('reject', req)"
                >
                  <XCircle :size="13" aria-hidden="true" />
                  <span>Từ chối</span>
                </button>
              </div>
              <button
                v-else-if="req.trangThai === 'APPROVED'"
                type="button"
                class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                @click="openModal('revoke', req)"
              >
                <XCircle :size="13" aria-hidden="true" />
                <span>Thu hồi</span>
              </button>
              <span v-else class="text-[11px] text-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Action Modal -->
    <div v-if="modalOpen && modalTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Xử lý yêu cầu tạm ngừng">
        <h2 class="text-base font-bold text-navy">
          {{ modalType === 'approve' ? 'Phê duyệt' : modalType === 'reject' ? 'Từ chối' : 'Thu hồi' }} yêu cầu #{{ modalTarget.maYeuCau }}
        </h2>
        <p class="mt-1 text-xs leading-relaxed text-muted">
          <span v-if="modalType === 'approve'">Chuyên gia sẽ không nhận thêm nhiệm vụ mới trong khoảng thời gian đã duyệt. Các nhiệm vụ đã giao trước đó vẫn giữ nguyên.</span>
          <span v-else-if="modalType === 'reject'">Bắt buộc nhập lý do từ chối để thông báo tới chuyên gia.</span>
          <span v-else>Thu hồi lịch tạm ngừng sẽ đưa chuyên gia trở lại trạng thái sẵn sàng và đánh thức các công việc WAITING_ELIGIBLE.</span>
        </p>

        <UiAlert v-if="modalError" class="mt-3" variant="danger" :message="modalError" />

        <label class="mt-4 block text-xs font-semibold text-navy">
          {{ modalType === 'approve' ? 'Ghi chú (không bắt buộc)' : 'Lý do bắt buộc' }}
          <span v-if="modalType !== 'approve'" class="text-danger">*</span>
          <textarea
            v-model="modalNote"
            rows="3"
            placeholder="Nhập nội dung..."
            class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none"
          />
        </label>

        <div class="mt-5 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle"
            :disabled="modalBusy"
            @click="modalOpen = false"
          >
            Hủy bỏ
          </button>
          <button
            type="button"
            class="rounded-lg px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
            :class="modalType === 'approve' ? 'bg-teal hover:bg-teal-dark' : 'bg-danger hover:bg-danger/90'"
            :disabled="modalBusy"
            @click="submitModal"
          >
            {{ modalBusy ? 'Đang xử lý...' : 'Xác nhận' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
