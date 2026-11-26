<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Search,
  X,
  XCircle,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  cancelAdminAssignment,
  extractApiError,
  fetchAdminAssignmentDetail,
  fetchAdminAssignments,
  fetchAdminWorkload,
  formatDateTimeVi,
  manualAssignExpert,
} from '@/service/adminPhase3ApiService'

const loading = ref(true)
const error = ref('')
const feedback = ref('')
const rows = ref([])
const workload = ref([])

const statusFilter = ref('')
const targetTypeFilter = ref('')
const expertFilter = ref('')
const searchQuery = ref('')
const limit = 20
const offset = ref(0)

// Detail modal
const detailOpen = ref(false)
const detailItem = ref(null)
const detailLoading = ref(false)

// Cancel modal
const cancelOpen = ref(false)
const cancelTarget = ref(null)
const cancelReason = ref('')
const cancelRequeue = ref(true)
const cancelBusy = ref(false)
const cancelError = ref('')

// Manual Exception Assignment modal (GĐ3.7)
const manualOpen = ref(false)
const manualTargetType = ref('COURSE')
const manualTargetId = ref('')
const manualExpertId = ref('')
const manualReason = ref('')
const manualBusy = ref(false)
const manualError = ref('')

function openManualModal() {
  manualTargetType.value = 'COURSE'
  manualTargetId.value = ''
  manualExpertId.value = ''
  manualReason.value = ''
  manualError.value = ''
  manualOpen.value = true
}

async function submitManualAssign() {
  if (!manualTargetId.value || !manualExpertId.value) {
    manualError.value = 'Vui lòng nhập mã đối tượng và chọn chuyên gia.'
    return
  }
  if (manualReason.value.trim().length < 5) {
    manualError.value = 'Bắt buộc nhập lý do phân công thủ công (tối thiểu 5 ký tự).'
    return
  }
  manualBusy.value = true
  manualError.value = ''
  try {
    const created = await manualAssignExpert({
      loaiDoiTuong: manualTargetType.value,
      maDoiTuong: Number(manualTargetId.value),
      maChuyenGia: Number(manualExpertId.value),
      lyDoPhanCong: manualReason.value.trim(),
    })
    manualOpen.value = false
    feedback.value = `Đã phân công thủ công #${created.maPhanCong} cho chuyên gia #${created.maChuyenGia}.`
    await loadData()
  } catch (err) {
    manualError.value = extractApiError(err, 'Không thể phân công thủ công.')
  } finally {
    manualBusy.value = false
  }
}

const STATUS_META = {
  ASSIGNED: { label: 'Chờ tiếp nhận', tone: 'warning' },
  ACCEPTED: { label: 'Đã tiếp nhận', tone: 'info' },
  IN_PROGRESS: { label: 'Đang kiểm duyệt', tone: 'teal' },
  COMPLETED: { label: 'Hoàn thành', tone: 'success' },
  DECLINED: { label: 'Từ chối', tone: 'danger' },
  EXPIRED: { label: 'Hết hạn tiếp nhận', tone: 'danger' },
  CANCELLED: { label: 'Đã thu hồi', tone: 'neutral' },
}

const filteredRows = computed(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase('vi')
  if (!q) return rows.value
  return rows.value.filter((item) => {
    const hay = [
      String(item.maPhanCong),
      item.tieuDeDoiTuong || '',
      item.tenChuyenGia || '',
      item.tenDanhMuc || '',
      item.loaiDoiTuong || '',
    ]
      .join(' ')
      .toLocaleLowerCase('vi')
    return hay.includes(q)
  })
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [list, wl] = await Promise.all([
      fetchAdminAssignments({
        status: statusFilter.value,
        targetType: targetTypeFilter.value,
        expertId: expertFilter.value ? Number(expertFilter.value) : null,
        limit,
        offset: offset.value,
      }),
      fetchAdminWorkload(),
    ])
    rows.value = Array.isArray(list) ? list : []
    workload.value = Array.isArray(wl) ? wl : []
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải danh sách phân công kiểm duyệt.')
  } finally {
    loading.value = false
  }
}

async function openDetail(item) {
  detailOpen.value = true
  detailItem.value = item
  detailLoading.value = true
  try {
    detailItem.value = await fetchAdminAssignmentDetail(item.maPhanCong)
  } catch {
    // keep summary item if detail fails
  } finally {
    detailLoading.value = false
  }
}

function openCancel(item) {
  cancelTarget.value = item
  cancelReason.value = ''
  cancelRequeue.value = true
  cancelError.value = ''
  cancelOpen.value = true
}

async function submitCancel() {
  if (!cancelTarget.value) return
  if (cancelReason.value.trim().length < 5) {
    cancelError.value = 'Vui lòng nhập lý do thu hồi tối thiểu 5 ký tự.'
    return
  }
  cancelBusy.value = true
  cancelError.value = ''
  try {
    await cancelAdminAssignment(cancelTarget.value.maPhanCong, {
      lyDoHuy: cancelReason.value.trim(),
      requeue: cancelRequeue.value,
    })
    cancelOpen.value = false
    feedback.value = `Đã thu hồi phân công #${cancelTarget.value.maPhanCong}${cancelRequeue.value ? ' và đưa lại vào hàng đợi phân công.' : '.'}`
    await loadData()
  } catch (err) {
    cancelError.value = extractApiError(err, 'Không thể thu hồi phân công.')
  } finally {
    cancelBusy.value = false
  }
}

function canCancel(item) {
  return ['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'].includes(item.trangThai)
}

watch([statusFilter, targetTypeFilter, expertFilter], () => {
  offset.value = 0
  loadData()
})

onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Kiểm duyệt tự động</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Quản lý phân công kiểm duyệt</h1>
        <p class="mt-1 text-sm text-muted">
          Giám sát phân công AUTO/MANUAL, điểm phù hợp chuyên môn, hạn xử lý và tải công việc từng chuyên gia.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-lg border border-teal/40 bg-teal/5 px-3 py-2 text-xs font-semibold text-teal-dark hover:bg-teal/10"
          @click="openManualModal"
        >
          Phân công thủ công (ngoại lệ)
        </button>
        <RouterLink
          :to="{ name: 'admin-review-monitor' }"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy hover:bg-subtle"
        >
          Mở hàng đợi phân công
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

    <UiAlert
      variant="info"
      title="Phân công tự động là quy trình chính"
      message="Hệ thống tự động chọn chuyên gia phù hợp nhất theo chuyên môn và tải mà không cần ADMIN xác nhận từng lượt. Chức năng Phân công thủ công chỉ dùng cho trường hợp ngoại lệ và vẫn bắt buộc vượt qua toàn bộ kiểm tra điều kiện (VERIFIED, chuyên môn, tải, tạm ngừng, xung đột lợi ích)."
    />

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Filters -->
    <div class="grid grid-cols-1 gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4">
      <label class="relative block">
        <span class="sr-only">Tìm kiếm phân công</span>
        <Search :size="15" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Tìm theo mã, tiêu đề, chuyên gia..."
          class="w-full rounded-lg border border-border bg-canvas py-2 pl-9 pr-3 text-xs text-ink focus:border-teal focus:outline-none"
        />
      </label>

      <select
        v-model="statusFilter"
        aria-label="Lọc theo trạng thái phân công"
        class="rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả trạng thái</option>
        <option v-for="(meta, key) in STATUS_META" :key="key" :value="key">{{ meta.label }} ({{ key }})</option>
      </select>

      <select
        v-model="targetTypeFilter"
        aria-label="Lọc theo loại nội dung"
        class="rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả loại nội dung</option>
        <option value="COURSE">Khóa học (COURSE)</option>
        <option value="MATERIAL">Tài liệu (MATERIAL)</option>
      </select>

      <select
        v-model="expertFilter"
        aria-label="Lọc theo chuyên gia"
        class="rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none"
      >
        <option value="">Tất cả chuyên gia</option>
        <option v-for="w in workload" :key="w.maChuyenGia" :value="String(w.maChuyenGia)">
          {{ w.hoTen || `Chuyên gia #${w.maChuyenGia}` }} ({{ w.activeAssignments }}/{{ w.maxAssignments }})
        </option>
      </select>
    </div>

    <!-- Assignments Table -->
    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <UiEmptyState
      v-else-if="filteredRows.length === 0"
      title="Chưa có bản ghi phân công phù hợp"
      description="Thay đổi bộ lọc hoặc kiểm tra hàng đợi phân công để xem các nội dung đang chờ xử lý."
    />

    <div v-else class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="min-w-full divide-y divide-border text-left text-xs">
        <thead class="bg-subtle/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
          <tr>
            <th class="px-4 py-3">Nội dung</th>
            <th class="px-4 py-3">Chuyên gia</th>
            <th class="px-4 py-3">Phương thức / Điểm</th>
            <th class="px-4 py-3">Vòng</th>
            <th class="px-4 py-3">Hạn tiếp nhận / Duyệt</th>
            <th class="px-4 py-3">Trạng thái</th>
            <th class="px-4 py-3 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/70">
          <tr v-for="item in filteredRows" :key="item.maPhanCong" class="hover:bg-subtle/40">
            <td class="px-4 py-3">
              <div class="flex items-center gap-1.5">
                <span class="rounded bg-subtle px-1.5 py-0.5 font-mono text-[10px] font-semibold text-navy">
                  {{ item.loaiDoiTuong }} #{{ item.maDoiTuong }}
                </span>
                <span class="font-mono text-[10px] text-muted">PC#{{ item.maPhanCong }}</span>
              </div>
              <p class="mt-1 max-w-xs truncate font-semibold text-navy">
                {{ item.tieuDeDoiTuong || `Nội dung #${item.maDoiTuong}` }}
              </p>
              <p class="text-[11px] text-muted">{{ item.tenDanhMuc || `Danh mục #${item.maDanhMuc}` }}</p>
            </td>

            <td class="px-4 py-3">
              <p class="font-semibold text-navy">{{ item.tenChuyenGia || `Chuyên gia #${item.maChuyenGia}` }}</p>
              <p class="font-mono text-[11px] text-muted">ID #{{ item.maChuyenGia }}</p>
            </td>

            <td class="px-4 py-3">
              <span class="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] font-semibold text-navy">
                {{ item.phuongThucPhanCong }}
              </span>
              <p class="mt-1 font-mono font-semibold text-teal tabular-nums">
                {{ item.diemPhuHop !== null && item.diemPhuHop !== undefined ? `${Number(item.diemPhuHop).toFixed(2)} điểm` : '—' }}
              </p>
            </td>

            <td class="px-4 py-3 font-mono font-semibold text-navy tabular-nums">
              Vòng {{ item.soVongKiemDuyet }}
            </td>

            <td class="px-4 py-3 tabular-nums">
              <p class="text-ink">Nhận: {{ formatDateTimeVi(item.hanTiepNhan) }}</p>
              <p class="text-muted">Duyệt: {{ formatDateTimeVi(item.hanKiemDuyet) }}</p>
              <p v-if="item.isOverdueReview" class="mt-0.5 inline-flex items-center gap-1 font-semibold text-danger">
                <AlertTriangle :size="12" aria-hidden="true" />
                <span>Quá hạn kiểm duyệt</span>
              </p>
            </td>

            <td class="px-4 py-3">
              <UiStatusBadge
                :tone="STATUS_META[item.trangThai]?.tone || 'neutral'"
                :label="STATUS_META[item.trangThai]?.label || item.trangThai"
              />
            </td>

            <td class="px-4 py-3 text-right">
              <div class="inline-flex items-center gap-1.5">
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-navy hover:bg-subtle"
                  @click="openDetail(item)"
                >
                  <Eye :size="13" aria-hidden="true" />
                  <span>Chi tiết</span>
                </button>
                <button
                  v-if="canCancel(item)"
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-danger/30 bg-danger/5 px-2.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/10"
                  @click="openCancel(item)"
                >
                  <XCircle :size="13" aria-hidden="true" />
                  <span>Thu hồi</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between">
      <p class="text-xs text-muted tabular-nums">
        Hiển thị {{ filteredRows.length }} bản ghi (offset {{ offset }})
      </p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="offset === 0"
          @click="offset = Math.max(0, offset - limit); loadData()"
        >
          <ChevronLeft :size="14" aria-hidden="true" />
          <span>Trang trước</span>
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="rows.length < limit"
          @click="offset += limit; loadData()"
        >
          <span>Trang sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="detailOpen && detailItem" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-2xl rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Chi tiết phân công">
        <div class="flex items-start justify-between gap-3 border-b border-border pb-3">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-teal">Phân công #{{ detailItem.maPhanCong }}</p>
            <h2 class="mt-0.5 text-lg font-bold text-navy">{{ detailItem.tieuDeDoiTuong || `${detailItem.loaiDoiTuong} #${detailItem.maDoiTuong}` }}</h2>
          </div>
          <button type="button" class="rounded-lg p-1.5 text-muted hover:bg-subtle" aria-label="Đóng" @click="detailOpen = false">
            <X :size="18" aria-hidden="true" />
          </button>
        </div>

        <div v-if="detailLoading" class="py-6">
          <UiSkeleton variant="text" :lines="4" />
        </div>
        <div v-else class="mt-4 space-y-4 text-xs">
          <div class="grid grid-cols-2 gap-3 rounded-lg bg-subtle/60 p-3.5 sm:grid-cols-3">
            <div><span class="text-muted">Chuyên gia:</span><p class="font-semibold text-navy">{{ detailItem.tenChuyenGia || `#${detailItem.maChuyenGia}` }}</p></div>
            <div><span class="text-muted">Trạng thái:</span><p class="mt-0.5"><UiStatusBadge :tone="STATUS_META[detailItem.trangThai]?.tone || 'neutral'" :label="STATUS_META[detailItem.trangThai]?.label || detailItem.trangThai" /></p></div>
            <div><span class="text-muted">Phương thức / Vòng:</span><p class="font-semibold text-navy">{{ detailItem.phuongThucPhanCong }} · Vòng {{ detailItem.soVongKiemDuyet }}</p></div>
            <div><span class="text-muted">Ngày phân công:</span><p class="font-medium text-ink tabular-nums">{{ formatDateTimeVi(detailItem.ngayPhanCong) }}</p></div>
            <div><span class="text-muted">Hạn tiếp nhận:</span><p class="font-medium text-ink tabular-nums">{{ formatDateTimeVi(detailItem.hanTiepNhan) }}</p></div>
            <div><span class="text-muted">Hạn kiểm duyệt:</span><p class="font-medium text-ink tabular-nums">{{ formatDateTimeVi(detailItem.hanKiemDuyet) }}</p></div>
          </div>

          <div v-if="detailItem.lyDoPhanCong">
            <p class="font-semibold text-navy">Lý do phân công</p>
            <p class="mt-1 rounded-lg border border-border bg-canvas p-3 text-slate-700">{{ detailItem.lyDoPhanCong }}</p>
          </div>

          <div v-if="detailItem.chiTietDiem">
            <p class="font-semibold text-navy">Chi tiết điểm phù hợp & lịch sử sự kiện (JSON)</p>
            <pre class="mt-1 max-h-48 overflow-auto rounded-lg border border-border bg-navy/95 p-3 font-mono text-[11px] text-slate-100">{{ JSON.stringify(detailItem.chiTietDiem, null, 2) }}</pre>
          </div>

          <div v-if="detailItem.lyDoTuChoi || detailItem.lyDoHuy" class="rounded-lg border border-danger/20 bg-danger/5 p-3 text-danger">
            <p v-if="detailItem.lyDoTuChoi"><strong>Lý do từ chối ({{ detailItem.maLyDoTuChoi }}):</strong> {{ detailItem.lyDoTuChoi }}</p>
            <p v-if="detailItem.lyDoHuy"><strong>Lý do thu hồi:</strong> {{ detailItem.lyDoHuy }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Cancel / Revoke Confirmation Modal -->
    <div v-if="cancelOpen && cancelTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Thu hồi nhiệm vụ kiểm duyệt">
        <h2 class="text-base font-bold text-navy">Thu hồi nhiệm vụ #{{ cancelTarget.maPhanCong }}</h2>
        <p class="mt-1 text-xs leading-relaxed text-muted">
          Bản nháp đánh giá (nếu có) sẽ được bảo toàn. Bắt buộc nhập lý do thu hồi để lưu vết quản trị.
        </p>

        <UiAlert v-if="cancelError" class="mt-3" variant="danger" :message="cancelError" />

        <div class="mt-4 space-y-3">
          <label class="block text-xs font-semibold text-navy">
            Lý do thu hồi <span class="text-danger">*</span>
            <textarea
              v-model="cancelReason"
              rows="3"
              placeholder="Nhập lý do thu hồi tối thiểu 5 ký tự..."
              class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none"
            />
          </label>

          <label class="flex items-center gap-2 text-xs text-ink">
            <input v-model="cancelRequeue" type="checkbox" class="size-4 rounded border-border text-teal focus:ring-teal" />
            <span>Đưa nội dung trở lại hàng đợi phân công tự động (`REASSIGN_CANCELLED`)</span>
          </label>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle"
            :disabled="cancelBusy"
            @click="cancelOpen = false"
          >
            Hủy bỏ
          </button>
          <button
            type="button"
            class="rounded-lg bg-danger px-4 py-2 text-xs font-semibold text-white hover:bg-danger/90 disabled:opacity-50"
            :disabled="cancelBusy"
            @click="submitCancel"
          >
            {{ cancelBusy ? 'Đang xử lý...' : 'Xác nhận thu hồi' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Manual Exception Assignment Modal (GĐ3.7) -->
    <div v-if="manualOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Phân công thủ công ngoại lệ">
        <h2 class="text-base font-bold text-navy">Phân công thủ công (Ngoại lệ)</h2>
        <p class="mt-1 text-xs leading-relaxed text-muted">
          Backend tự động kiểm tra đủ điều kiện (ACTIVE, VERIFIED, chuyên môn khớp danh mục, tải &lt; trần, không tạm ngừng, không xung đột lợi ích) và đóng job hàng đợi hiện hữu nguyên tử.
        </p>

        <UiAlert v-if="manualError" class="mt-3" variant="danger" :message="manualError" />

        <div class="mt-4 space-y-3 text-xs">
          <div class="grid grid-cols-2 gap-3">
            <label class="block font-semibold text-navy">
              Loại đối tượng
              <select v-model="manualTargetType" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none">
                <option value="COURSE">COURSE (Khóa học)</option>
                <option value="MATERIAL">MATERIAL (Tài liệu)</option>
              </select>
            </label>
            <label class="block font-semibold text-navy">
              Mã đối tượng <span class="text-danger">*</span>
              <input v-model="manualTargetId" type="number" min="1" placeholder="VD: 28" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs tabular-nums focus:border-teal focus:outline-none" />
            </label>
          </div>

          <label class="block font-semibold text-navy">
            Chọn chuyên gia <span class="text-danger">*</span>
            <select v-model="manualExpertId" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none">
              <option value="">-- Chọn chuyên gia --</option>
              <option v-for="w in workload" :key="w.maChuyenGia" :value="String(w.maChuyenGia)">
                {{ w.hoTen || `Chuyên gia #${w.maChuyenGia}` }} ({{ w.activeAssignments }}/{{ w.maxAssignments }} · {{ w.trangThaiHoSo }})
              </option>
            </select>
          </label>

          <label class="block font-semibold text-navy">
            Lý do phân công thủ công <span class="text-danger">*</span>
            <textarea v-model="manualReason" rows="3" placeholder="Ghi rõ lý do ngoại lệ (tối thiểu 5 ký tự)..." class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none" />
          </label>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle" :disabled="manualBusy" @click="manualOpen = false">
            Hủy bỏ
          </button>
          <button type="button" class="rounded-lg bg-teal px-4 py-2 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50" :disabled="manualBusy" @click="submitManualAssign">
            {{ manualBusy ? 'Đang phân công...' : 'Xác nhận phân công' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
