<script setup>
import { onMounted, ref, watch } from 'vue'
import { CheckCircle2, Lock, RefreshCw, ShieldAlert, Unlock, XCircle } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  confirmViolation,
  exemptViolation,
  extractApiError,
  fetchAccountabilityAuditLogs,
  fetchAccountabilityExperts,
  fetchAccountabilityViolations,
  formatDateTimeVi,
  lockExpertAccount,
  unlockExpertAccount,
} from '@/service/adminPhase3ApiService'

const activeTab = ref('experts') // 'experts' | 'violations' | 'audit'
const loading = ref(true)
const error = ref('')
const feedback = ref('')

const experts = ref([])
const violations = ref([])
const auditLogs = ref([])
const violationStatusFilter = ref('')

// Action modal (lock / unlock / confirm / exempt)
const modalOpen = ref(false)
const modalType = ref('') // 'lock' | 'unlock' | 'confirm' | 'exempt'
const modalTarget = ref(null)
const modalNote = ref('')
const modalBusy = ref(false)
const modalError = ref('')

const DISCIPLINE_META = {
  NORMAL: { label: 'Bình thường', tone: 'success' },
  WARNING: { label: 'Cảnh báo', tone: 'warning' },
  FINAL_WARNING: { label: 'Cảnh báo cuối', tone: 'amber' },
  LOCKED: { label: 'Đã khóa', tone: 'danger' },
}

const VIOLATION_STATUS_META = {
  PENDING_REVIEW: { label: 'Chờ xem xét', tone: 'warning' },
  CONFIRMED: { label: 'Đã xác nhận', tone: 'danger' },
  EXEMPTED: { label: 'Đã miễn trừ', tone: 'success' },
}

async function loadTab() {
  loading.value = true
  error.value = ''
  try {
    if (activeTab.value === 'experts') {
      experts.value = await fetchAccountabilityExperts()
    } else if (activeTab.value === 'violations') {
      violations.value = await fetchAccountabilityViolations({
        status: violationStatusFilter.value,
        limit: 50,
      })
    } else {
      auditLogs.value = await fetchAccountabilityAuditLogs({ limit: 50 })
    }
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải dữ liệu kỷ luật chuyên gia.')
  } finally {
    loading.value = false
  }
}

function openModal(type, target) {
  modalType.value = type
  modalTarget.value = target
  modalNote.value = ''
  modalError.value = ''
  modalOpen.value = true
}

function modalTitle() {
  if (modalType.value === 'lock') return `Khóa tài khoản chuyên gia #${modalTarget.value?.maChuyenGia}`
  if (modalType.value === 'unlock') return `Mở khóa chuyên gia #${modalTarget.value?.maChuyenGia}`
  if (modalType.value === 'confirm') return `Xác nhận vi phạm #${modalTarget.value?.maViPham}`
  return `Miễn trừ vi phạm #${modalTarget.value?.maViPham}`
}

async function submitModal() {
  if (modalNote.value.trim().length < 5) {
    modalError.value = 'Vui lòng nhập lý do/ghi chú tối thiểu 5 ký tự.'
    return
  }
  modalBusy.value = true
  modalError.value = ''
  try {
    const note = modalNote.value.trim()
    if (modalType.value === 'lock') {
      await lockExpertAccount(modalTarget.value.maChuyenGia, note)
      feedback.value = `Đã khóa tài khoản chuyên gia #${modalTarget.value.maChuyenGia} và thu hồi nhiệm vụ đang mở.`
    } else if (modalType.value === 'unlock') {
      await unlockExpertAccount(modalTarget.value.maChuyenGia, note)
      feedback.value = `Đã mở khóa chuyên gia #${modalTarget.value.maChuyenGia} và mở chu kỳ kỷ luật mới.`
    } else if (modalType.value === 'confirm') {
      await confirmViolation(modalTarget.value.maViPham, note)
      feedback.value = `Đã xác nhận vi phạm #${modalTarget.value.maViPham}.`
    } else if (modalType.value === 'exempt') {
      await exemptViolation(modalTarget.value.maViPham, note)
      feedback.value = `Đã miễn trừ vi phạm #${modalTarget.value.maViPham}.`
    }
    modalOpen.value = false
    await loadTab()
  } catch (err) {
    modalError.value = extractApiError(err, 'Không thể thực hiện thao tác kỷ luật.')
  } finally {
    modalBusy.value = false
  }
}

watch([activeTab, violationStatusFilter], loadTab)
onMounted(loadTab)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Kỷ luật & Trách nhiệm</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Quản lý vi phạm và kỷ luật chuyên gia</h1>
        <p class="mt-1 text-sm text-muted">
          Cửa sổ trượt 168 giờ (7 ngày liên tục) · Cảnh báo từ 2 · Cảnh báo cuối ở 3 · Tự động khóa từ 4 · Chỉ ADMIN mở khóa.
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white hover:bg-navy/90"
        :disabled="loading"
        @click="loadTab"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Tabs -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="inline-flex rounded-lg border border-border bg-subtle p-1" role="tablist" aria-label="Mục quản lý kỷ luật">
        <button
          v-for="tab in [
            { id: 'experts', label: 'Trạng thái chuyên gia' },
            { id: 'violations', label: 'Danh sách vi phạm' },
            { id: 'audit', label: 'Nhật ký kỷ luật (chỉ đọc)' },
          ]"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.id"
          class="rounded-md px-3 py-1.5 text-xs font-semibold transition-colors"
          :class="activeTab === tab.id ? 'bg-surface text-navy shadow-sm' : 'text-muted hover:text-navy'"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <select
        v-if="activeTab === 'violations'"
        v-model="violationStatusFilter"
        aria-label="Lọc trạng thái vi phạm"
        class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả trạng thái</option>
        <option value="PENDING_REVIEW">Chờ xem xét (PENDING_REVIEW)</option>
        <option value="CONFIRMED">Đã xác nhận (CONFIRMED)</option>
        <option value="EXEMPTED">Đã miễn trừ (EXEMPTED)</option>
      </select>
    </div>

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <!-- Tab 1: Experts -->
    <template v-else-if="activeTab === 'experts'">
      <UiEmptyState
        v-if="experts.length === 0"
        :icon="ShieldAlert"
        title="Chưa có dữ liệu chuyên gia"
        description="Hệ thống chưa ghi nhận tài khoản EXPERT nào."
      />
      <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-left text-xs">
          <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th class="px-4 py-3">Chuyên gia</th>
              <th class="px-4 py-3">Tài khoản / Hồ sơ</th>
              <th class="px-4 py-3">Chu kỳ</th>
              <th class="px-4 py-3">Vi phạm (168h)</th>
              <th class="px-4 py-3">Chờ duyệt</th>
              <th class="px-4 py-3">Mức kỷ luật</th>
              <th class="px-4 py-3 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/70">
            <tr v-for="exp in experts" :key="exp.maChuyenGia" class="hover:bg-subtle/40">
              <td class="px-4 py-3">
                <p class="font-semibold text-navy">{{ exp.hoTen || `Chuyên gia #${exp.maChuyenGia}` }}</p>
                <p class="font-mono text-[11px] text-muted">CG#{{ exp.maChuyenGia }} · ND#{{ exp.maNguoiDung }}</p>
              </td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1.5">
                  <UiStatusBadge
                    :tone="exp.trangThaiTaiKhoan === 'LOCKED' ? 'danger' : 'success'"
                    :label="exp.trangThaiTaiKhoan"
                  />
                  <UiStatusBadge
                    :tone="exp.trangThaiHoSo === 'VERIFIED' ? 'teal' : 'warning'"
                    :label="exp.trangThaiHoSo"
                  />
                </div>
              </td>
              <td class="px-4 py-3 font-mono font-semibold text-navy tabular-nums">Chu kỳ #{{ exp.currentCycle }}</td>
              <td class="px-4 py-3 font-mono font-bold text-navy tabular-nums">{{ exp.confirmedViolationsInWindow }}</td>
              <td class="px-4 py-3 font-mono text-amber-dark font-semibold tabular-nums">{{ exp.pendingReviewCount }}</td>
              <td class="px-4 py-3">
                <UiStatusBadge
                  :tone="DISCIPLINE_META[exp.disciplineLevel]?.tone || 'neutral'"
                  :label="DISCIPLINE_META[exp.disciplineLevel]?.label || exp.disciplineLevel"
                />
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="exp.trangThaiTaiKhoan === 'LOCKED'"
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg bg-teal px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-teal-dark"
                  @click="openModal('unlock', exp)"
                >
                  <Unlock :size="13" aria-hidden="true" />
                  <span>Mở khóa</span>
                </button>
                <button
                  v-else
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                  @click="openModal('lock', exp)"
                >
                  <Lock :size="13" aria-hidden="true" />
                  <span>Khóa tài khoản</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Tab 2: Violations -->
    <template v-else-if="activeTab === 'violations'">
      <UiEmptyState
        v-if="violations.length === 0"
        title="Không có bản ghi vi phạm"
        description="Chưa có vi phạm nào khớp với bộ lọc trạng thái đang chọn."
      />
      <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-left text-xs">
          <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th class="px-4 py-3">Mã / Chuyên gia</th>
              <th class="px-4 py-3">Loại vi phạm / Lý do</th>
              <th class="px-4 py-3">Chu kỳ</th>
              <th class="px-4 py-3">Thời điểm</th>
              <th class="px-4 py-3">Trạng thái</th>
              <th class="px-4 py-3 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/70">
            <tr v-for="vp in violations" :key="vp.maViPham" class="hover:bg-subtle/40">
              <td class="px-4 py-3">
                <p class="font-mono font-bold text-navy">VP#{{ vp.maViPham }}</p>
                <p class="text-[11px] text-muted">CG#{{ vp.maChuyenGia }} · PC#{{ vp.maPhanCong }}</p>
              </td>
              <td class="px-4 py-3 max-w-sm">
                <p class="font-semibold text-navy">{{ vp.loaiViPham }}</p>
                <p v-if="vp.maLyDoTuChoi" class="font-mono text-[11px] text-muted">{{ vp.maLyDoTuChoi }}</p>
                <p v-if="vp.lyDo" class="mt-0.5 text-slate-600">{{ vp.lyDo }}</p>
                <p v-if="vp.ghiChuXuLy" class="mt-0.5 text-[11px] text-teal-dark">Ghi chú ADMIN: {{ vp.ghiChuXuLy }}</p>
              </td>
              <td class="px-4 py-3 font-mono font-semibold text-navy tabular-nums">#{{ vp.chuKyKyLuatSo }}</td>
              <td class="px-4 py-3 tabular-nums text-ink">{{ formatDateTimeVi(vp.ngayViPham) }}</td>
              <td class="px-4 py-3">
                <UiStatusBadge
                  :tone="VIOLATION_STATUS_META[vp.trangThaiXuLy]?.tone || 'neutral'"
                  :label="VIOLATION_STATUS_META[vp.trangThaiXuLy]?.label || vp.trangThaiXuLy"
                />
              </td>
              <td class="px-4 py-3 text-right">
                <div v-if="vp.trangThaiXuLy === 'PENDING_REVIEW'" class="inline-flex items-center gap-1.5">
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                    @click="openModal('confirm', vp)"
                  >
                    <XCircle :size="13" aria-hidden="true" />
                    <span>Xác nhận</span>
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded-lg bg-teal px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-teal-dark"
                    @click="openModal('exempt', vp)"
                  >
                    <CheckCircle2 :size="13" aria-hidden="true" />
                    <span>Miễn trừ</span>
                  </button>
                </div>
                <span v-else class="text-[11px] text-muted">Đã xử lý</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Tab 3: Insert-only Audit Logs -->
    <template v-else>
      <UiAlert
        variant="info"
        message="Nhật ký kỷ luật (NhatKyKyLuatChuyenGia) là dữ liệu bất biến (chỉ ghi thêm), không cho phép chỉnh sửa hoặc xóa."
      />
      <UiEmptyState
        v-if="auditLogs.length === 0"
        title="Chưa có lịch sử kỷ luật"
        description="Các hành động cảnh báo, khóa, mở khóa, xác nhận hoặc miễn trừ vi phạm sẽ được lưu vết tại đây."
      />
      <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="min-w-full divide-y divide-border text-left text-xs">
          <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th class="px-4 py-3">Thời điểm</th>
              <th class="px-4 py-3">Hành động</th>
              <th class="px-4 py-3">Chuyên gia / Chu kỳ</th>
              <th class="px-4 py-3">Nguồn thực hiện</th>
              <th class="px-4 py-3">Chuyển trạng thái</th>
              <th class="px-4 py-3">Lý do</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/70">
            <tr v-for="log in auditLogs" :key="log.maNhatKy" class="hover:bg-subtle/40">
              <td class="px-4 py-3 tabular-nums text-ink">{{ formatDateTimeVi(log.ngayTao) }}</td>
              <td class="px-4 py-3 font-mono font-semibold text-navy">{{ log.hanhDong }}</td>
              <td class="px-4 py-3 font-mono text-navy">CG#{{ log.maChuyenGia }} · Chu kỳ #{{ log.chuKyKyLuatSo }}</td>
              <td class="px-4 py-3 text-muted">{{ log.nguonTacDong }}</td>
              <td class="px-4 py-3 font-mono text-[11px]">{{ log.trangThaiTruoc || '—' }} → {{ log.trangThaiSau || '—' }}</td>
              <td class="px-4 py-3 max-w-sm text-slate-700">{{ log.lyDo || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Confirmation Modal -->
    <div v-if="modalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" :aria-label="modalTitle()">
        <h2 class="text-base font-bold text-navy">{{ modalTitle() }}</h2>
        <p class="mt-1 text-xs leading-relaxed text-muted">
          <span v-if="modalType === 'lock'">Tài khoản sẽ chuyển sang LOCKED, thu hồi toàn bộ nhiệm vụ đang mở và lưu vết vào nhật ký kỷ luật.</span>
          <span v-else-if="modalType === 'unlock'">Tài khoản sẽ mở khóa về ACTIVE, tăng chu kỳ kỷ luật mới và vô hiệu hóa mọi phiên JWT phát hành trước mốc mở khóa.</span>
          <span v-else-if="modalType === 'confirm'">Xác nhận vi phạm sẽ tính vào cửa sổ 168 giờ hiện tại và đánh giá lại ngưỡng cảnh báo/khóa.</span>
          <span v-else>Miễn trừ vi phạm sẽ không tính vào ngưỡng kỷ luật của chuyên gia.</span>
        </p>

        <UiAlert v-if="modalError" class="mt-3" variant="danger" :message="modalError" />

        <label class="mt-4 block text-xs font-semibold text-navy">
          Lý do / Ghi chú xử lý <span class="text-danger">*</span>
          <textarea
            v-model="modalNote"
            rows="3"
            placeholder="Nhập lý do chi tiết (tối thiểu 5 ký tự)..."
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
            :class="modalType === 'lock' || modalType === 'confirm' ? 'bg-danger hover:bg-danger/90' : 'bg-teal hover:bg-teal-dark'"
            :disabled="modalBusy"
            @click="submitModal"
          >
            {{ modalBusy ? 'Đang xử lý...' : 'Xác nhận thực hiện' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
