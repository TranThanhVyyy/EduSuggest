<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RefreshCw, Save, Settings2 } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  extractApiError,
  fetchAssignmentConfig,
  formatDateTimeVi,
  updateAssignmentConfig,
} from '@/service/adminPhase3ApiService'

const loading = ref(true)
const saving = ref(false)
const confirmOpen = ref(false)
const error = ref('')
const feedback = ref('')
const lastUpdated = ref(null)

const form = reactive({
  gioiHanTaiToiDa: 5,
  hanTiepNhanGio: 24,
  hanKiemDuyetGio: 72,
  soLanTaiPhanCongToiDa: 5,
  khoangThongKeGio: 168,
  nguongCanhBao: 2,
  nguongKhoaTaiKhoan: 4,
  thoiGianTamNgungToiDaNgay: 30,
  tinhViPhamHetHan: true,
  tuDongKhoa: true,
  uuTienTuyetDoiChuyenMonChinh: false,
})

function applyConfig(cfg) {
  form.gioiHanTaiToiDa = Number(cfg.gioiHanTaiToiDa)
  form.hanTiepNhanGio = Number(cfg.hanTiepNhanGio)
  form.hanKiemDuyetGio = Number(cfg.hanKiemDuyetGio)
  form.soLanTaiPhanCongToiDa = Number(cfg.soLanTaiPhanCongToiDa)
  form.khoangThongKeGio = Number(cfg.khoangThongKeGio)
  form.nguongCanhBao = Number(cfg.nguongCanhBao)
  form.nguongKhoaTaiKhoan = Number(cfg.nguongKhoaTaiKhoan)
  form.thoiGianTamNgungToiDaNgay = Number(cfg.thoiGianTamNgungToiDaNgay)
  form.tinhViPhamHetHan = Boolean(cfg.tinhViPhamHetHan)
  form.tuDongKhoa = Boolean(cfg.tuDongKhoa)
  form.uuTienTuyetDoiChuyenMonChinh = Boolean(cfg.uuTienTuyetDoiChuyenMonChinh)
  lastUpdated.value = cfg.ngayCapNhat || null
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const cfg = await fetchAssignmentConfig()
    applyConfig(cfg)
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải cấu hình hệ thống phân công.')
  } finally {
    loading.value = false
  }
}

function requestSave() {
  error.value = ''
  if (form.nguongKhoaTaiKhoan <= form.nguongCanhBao) {
    error.value = 'Ngưỡng khóa tài khoản phải lớn hơn ngưỡng cảnh báo.'
    return
  }
  confirmOpen.value = true
}

async function confirmSave() {
  saving.value = true
  error.value = ''
  feedback.value = ''
  try {
    const updated = await updateAssignmentConfig({ ...form })
    applyConfig(updated)
    confirmOpen.value = false
    feedback.value = 'Đã lưu cấu hình phân công thành công. Thay đổi chỉ áp dụng cho sự kiện mới, không làm thay đổi dữ liệu lịch sử.'
  } catch (err) {
    confirmOpen.value = false
    error.value = extractApiError(err, 'Không thể lưu cấu hình phân công.')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="max-w-4xl space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Tham số vận hành</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Cấu hình hệ thống phân công</h1>
        <p class="mt-1 text-sm text-muted">
          Quản lý tập trung bảng <code>CauHinhPhanCong</code>. Cập nhật không tự động khóa hàng loạt hoặc sửa đổi dữ liệu lịch sử.
          <span v-if="lastUpdated" class="ml-1 tabular-nums">(Lưu gần nhất: {{ formatDateTimeVi(lastUpdated) }})</span>
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy hover:bg-subtle"
        :disabled="loading"
        @click="loadData"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Tải lại</span>
      </button>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <form v-else class="space-y-6" @submit.prevent="requestSave">
      <!-- Group 1: Load & SLA -->
      <section class="rounded-xl border border-border bg-surface p-5 space-y-4">
        <div class="flex items-center gap-2 border-b border-border/70 pb-3">
          <Settings2 :size="16" class="text-teal" aria-hidden="true" />
          <h2 class="text-sm font-bold text-navy">Tải công việc, thời hạn & tạm ngừng</h2>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label class="block text-xs font-semibold text-navy">
            Tải tối đa / chuyên gia
            <input v-model.number="form.gioiHanTaiToiDa" type="number" min="1" max="50" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Hạn tiếp nhận (giờ)
            <input v-model.number="form.hanTiepNhanGio" type="number" min="1" max="168" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Hạn kiểm duyệt (giờ)
            <input v-model.number="form.hanKiemDuyetGio" type="number" min="1" max="720" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Tái phân công tối đa (lần)
            <input v-model.number="form.soLanTaiPhanCongToiDa" type="number" min="1" max="20" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Tạm ngừng tối đa (ngày)
            <input v-model.number="form.thoiGianTamNgungToiDaNgay" type="number" min="1" max="180" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
        </div>
      </section>

      <!-- Group 2: Accountability Thresholds -->
      <section class="rounded-xl border border-border bg-surface p-5 space-y-4">
        <div class="border-b border-border/70 pb-3">
          <h2 class="text-sm font-bold text-navy">Ngưỡng kỷ luật & cửa sổ thống kê</h2>
          <p class="text-xs text-muted">Ngưỡng khóa phải lớn hơn ngưỡng cảnh báo.</p>
        </div>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label class="block text-xs font-semibold text-navy">
            Khoảng thống kê vi phạm (giờ)
            <input v-model.number="form.khoangThongKeGio" type="number" min="24" max="2160" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Ngưỡng cảnh báo
            <input v-model.number="form.nguongCanhBao" type="number" min="1" max="20" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
          <label class="block text-xs font-semibold text-navy">
            Ngưỡng khóa tài khoản
            <input v-model.number="form.nguongKhoaTaiKhoan" type="number" min="2" max="50" required class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm tabular-nums focus:border-teal focus:outline-none" />
          </label>
        </div>
      </section>

      <!-- Group 3: Boolean Policies -->
      <section class="rounded-xl border border-border bg-surface p-5 space-y-3">
        <h2 class="border-b border-border/70 pb-3 text-sm font-bold text-navy">Chính sách tự động</h2>
        <label class="flex items-start gap-3 rounded-lg border border-border/80 bg-canvas p-3 text-xs">
          <input v-model="form.tinhViPhamHetHan" type="checkbox" class="mt-0.5 size-4 rounded border-border text-teal focus:ring-teal" />
          <span><strong class="text-navy">Tính vi phạm khi hết hạn tiếp nhận</strong><br /><span class="text-muted">Ghi nhận vi phạm EXPIRED_ACCEPTANCE khi chuyên gia bỏ lỡ hạn tiếp nhận.</span></span>
        </label>
        <label class="flex items-start gap-3 rounded-lg border border-border/80 bg-canvas p-3 text-xs">
          <input v-model="form.tuDongKhoa" type="checkbox" class="mt-0.5 size-4 rounded border-border text-teal focus:ring-teal" />
          <span><strong class="text-navy">Tự động khóa tài khoản khi đạt ngưỡng</strong><br /><span class="text-muted">Tự động chuyển tài khoản EXPERT sang LOCKED khi đạt số vi phạm xác nhận trong cửa sổ trượt.</span></span>
        </label>
        <label class="flex items-start gap-3 rounded-lg border border-border/80 bg-canvas p-3 text-xs">
          <input v-model="form.uuTienTuyetDoiChuyenMonChinh" type="checkbox" class="mt-0.5 size-4 rounded border-border text-teal focus:ring-teal" />
          <span><strong class="text-navy">Ưu tiên tuyệt đối chuyên môn chính</strong><br /><span class="text-muted">Luôn xếp ứng viên khớp chuyên môn chính lên trước chuyên môn phụ khi chấm điểm phân công.</span></span>
        </label>
      </section>

      <div class="flex justify-end">
        <button
          type="submit"
          class="inline-flex items-center gap-2 rounded-lg bg-navy px-5 py-2.5 text-xs font-semibold text-white hover:bg-navy/90 disabled:opacity-50"
          :disabled="saving"
        >
          <Save :size="15" aria-hidden="true" />
          <span>Lưu cấu hình phân công</span>
        </button>
      </div>
    </form>

    <!-- Confirm Save Modal -->
    <div v-if="confirmOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Xác nhận lưu cấu hình">
        <h2 class="text-base font-bold text-navy">Xác nhận cập nhật cấu hình phân công</h2>
        <p class="mt-2 text-xs leading-relaxed text-muted">
          Các tham số mới sẽ được lưu vào <code>CauHinhPhanCong</code> và áp dụng cho các lượt phân công/vi phạm phát sinh từ thời điểm này. Dữ liệu lịch sử và trạng thái tài khoản hiện tại sẽ không bị thay đổi hồi tố.
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle" :disabled="saving" @click="confirmOpen = false">
            Hủy bỏ
          </button>
          <button type="button" class="rounded-lg bg-teal px-4 py-2 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50" :disabled="saving" @click="confirmSave">
            {{ saving ? 'Đang lưu...' : 'Xác nhận lưu' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
