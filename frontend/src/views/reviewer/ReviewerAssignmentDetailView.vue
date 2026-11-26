<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  FileText,
  Play,
  Save,
  Send,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'
import { openMaterialFile } from '@/service/materialFileService'
import {
  acceptMyAssignment,
  extractApiError,
  fetchMyAssignmentDetail,
  saveMyAssignmentDraft,
  startMyAssignment,
  submitMyAssignmentDecision,
} from '@/service/expertPhase3ApiService'

const route = useRoute()
const router = useRouter()
const assignmentId = computed(() => Number(route.params.assignmentId))

const loading = ref(true)
const error = ref('')
const feedback = ref('')
const detail = ref(null)

const savingDraft = ref(false)
const lastDraftSavedAt = ref('')
const isDirty = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const actionBusy = ref(false)
const openingMaterialId = ref('')

const form = reactive({
  trangThai: 'APPROVED',
  diemKyThuat: '',
  diemNoiDung: '',
  noiDungDanhGia: '',
  ghiChu: '',
})

const canEditReview = computed(() =>
  ['ACCEPTED', 'IN_PROGRESS'].includes(detail.value?.trangThai || ''),
)
const isCourse = computed(() => detail.value?.loaiDoiTuong === 'COURSE')
const content = computed(() => detail.value?.noiDungKiemDuyet || null)

function markDirty() {
  isDirty.value = true
}

async function openReviewMaterial(material) {
  openingMaterialId.value = String(material.maTaiLieu)
  error.value = ''
  try {
    await openMaterialFile({
      id: material.maTaiLieu,
      fileUrl: material.duongDanTep,
      title: material.tieuDe,
    })
  } catch (err) {
    error.value = extractApiError(err, 'Không thể mở tệp. Assignment có thể đã hết hiệu lực hoặc eligibility đã thay đổi.')
  } finally {
    openingMaterialId.value = ''
  }
}

function hydrateDraft(draft) {
  if (!draft || typeof draft !== 'object') return
  if (draft.trangThai) form.trangThai = draft.trangThai
  if (draft.diemKyThuat !== undefined && draft.diemKyThuat !== null) form.diemKyThuat = String(draft.diemKyThuat)
  if (draft.diemNoiDung !== undefined && draft.diemNoiDung !== null) form.diemNoiDung = String(draft.diemNoiDung)
  if (draft.noiDungDanhGia) form.noiDungDanhGia = draft.noiDungDanhGia
  if (draft.ghiChu) form.ghiChu = draft.ghiChu
}

async function loadDetail() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchMyAssignmentDetail(assignmentId.value)
    detail.value = data
    if (data?.banNhapDanhGia) {
      hydrateDraft(data.banNhapDanhGia)
    }
    isDirty.value = false
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải chi tiết nhiệm vụ kiểm duyệt. Có thể nhiệm vụ đã hết hiệu lực hoặc bạn không có quyền truy cập.')
  } finally {
    loading.value = false
  }
}

async function handleAccept() {
  actionBusy.value = true
  error.value = ''
  try {
    await acceptMyAssignment(assignmentId.value)
    feedback.value = 'Đã tiếp nhận nhiệm vụ thành công. Nội dung kiểm duyệt đã được mở khóa.'
    await loadDetail()
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tiếp nhận nhiệm vụ.')
  } finally {
    actionBusy.value = false
  }
}

async function handleStart() {
  actionBusy.value = true
  error.value = ''
  try {
    await startMyAssignment(assignmentId.value)
    feedback.value = 'Nhiệm vụ đã chuyển sang trạng thái ĐANG KIỂM DUYỆT (IN_PROGRESS).'
    await loadDetail()
  } catch (err) {
    error.value = extractApiError(err, 'Không thể bắt đầu kiểm duyệt.')
  } finally {
    actionBusy.value = false
  }
}

async function handleSaveDraft() {
  if (savingDraft.value || !canEditReview.value) return
  savingDraft.value = true
  error.value = ''
  try {
    await saveMyAssignmentDraft(assignmentId.value, {
      trangThai: form.trangThai,
      diemKyThuat: form.diemKyThuat !== '' ? Number(form.diemKyThuat) : null,
      diemNoiDung: form.diemNoiDung !== '' ? Number(form.diemNoiDung) : null,
      noiDungDanhGia: form.noiDungDanhGia,
      ghiChu: form.ghiChu,
      savedAt: new Date().toISOString(),
    })
    isDirty.value = false
    lastDraftSavedAt.value = formatDateTimeVi(new Date().toISOString())
    feedback.value = 'Đã lưu bản nháp đánh giá thành công.'
  } catch (err) {
    error.value = extractApiError(err, 'Không thể lưu bản nháp.')
  } finally {
    savingDraft.value = false
  }
}

function requestDecisionSubmit() {
  error.value = ''
  const hasNote = form.ghiChu.trim().length > 0 || form.noiDungDanhGia.trim().length > 0
  if (form.trangThai !== 'APPROVED' && !hasNote) {
    error.value = 'Bắt buộc nhập nhận xét hoặc ghi chú khi từ chối hoặc yêu cầu chỉnh sửa.'
    return
  }
  confirmOpen.value = true
}

async function confirmDecisionSubmit() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await submitMyAssignmentDecision(assignmentId.value, {
      trangThai: form.trangThai,
      noiDungDanhGia: form.noiDungDanhGia.trim() || null,
      ghiChu: form.ghiChu.trim() || null,
      diemKyThuat: form.diemKyThuat !== '' ? Number(form.diemKyThuat) : null,
      diemNoiDung: form.diemNoiDung !== '' ? Number(form.diemNoiDung) : null,
    })
    isDirty.value = false
    confirmOpen.value = false
    feedback.value = 'Đã gửi quyết định kiểm duyệt chính thức thành công.'
    await loadDetail()
  } catch (err) {
    confirmOpen.value = false
    error.value = extractApiError(err, 'Không thể gửi quyết định kiểm duyệt.')
  } finally {
    submitting.value = false
  }
}

function beforeUnloadHandler(e) {
  if (isDirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onBeforeRouteLeave(() => {
  if (isDirty.value) {
    return window.confirm('Bạn có thay đổi bản nháp chưa lưu. Bạn chắc chắn muốn rời trang?')
  }
  return true
})

onMounted(() => {
  loadDetail()
  window.addEventListener('beforeunload', beforeUnloadHandler)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnloadHandler)
})
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-navy hover:bg-subtle"
          @click="router.push({ name: 'reviewer-assignments' })"
        >
          <ArrowLeft :size="14" aria-hidden="true" />
          <span>Quay lại</span>
        </button>
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-teal">Không gian kiểm duyệt · PC#{{ assignmentId }}</p>
          <h1 class="text-xl font-bold text-navy">{{ detail?.tieuDeDoiTuong || `Nhiệm vụ #${assignmentId}` }}</h1>
        </div>
      </div>

      <div v-if="detail" class="flex items-center gap-2">
        <UiStatusBadge
          :tone="detail.trangThai === 'COMPLETED' ? 'success' : detail.trangThai === 'IN_PROGRESS' ? 'teal' : detail.trangThai === 'ASSIGNED' ? 'warning' : 'info'"
          :label="detail.trangThai"
        />
        <button
          v-if="detail.trangThai === 'ASSIGNED' && detail.allowedActions?.includes('accept')"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-teal px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50"
          :disabled="actionBusy"
          @click="handleAccept"
        >
          <CheckCircle2 :size="14" aria-hidden="true" />
          <span>Tiếp nhận nhiệm vụ</span>
        </button>
        <button
          v-if="detail.trangThai === 'ACCEPTED' && detail.allowedActions?.includes('start')"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white hover:bg-navy/90 disabled:opacity-50"
          :disabled="actionBusy"
          @click="handleStart"
        >
          <Play :size="14" aria-hidden="true" />
          <span>Bắt đầu kiểm duyệt</span>
        </button>
      </div>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <template v-else-if="detail">
      <!-- Gate for ASSIGNED (not yet accepted) -->
      <UiAlert
        v-if="detail.trangThai === 'ASSIGNED'"
        variant="info"
        title="Nội dung chi tiết chỉ mở sau khi bạn tiếp nhận nhiệm vụ"
        :message="`Hạn tiếp nhận: ${formatDateTimeVi(detail.hanTiepNhan)}. Vui lòng bấm Tiếp nhận để xem toàn bộ bài học/tài liệu và bắt đầu đánh giá.`"
      />

      <!-- Workspace Grid (2 cols on desktop) -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <!-- Left 7 cols: Content Inspection -->
        <div class="space-y-4 lg:col-span-7">
          <section class="rounded-xl border border-border bg-surface p-5 space-y-3">
            <div class="flex items-center gap-2 border-b border-border/70 pb-3">
              <component :is="isCourse ? BookOpen : FileText" :size="16" class="text-teal" aria-hidden="true" />
              <h2 class="text-sm font-bold text-navy">
                {{ isCourse ? 'Thông tin khóa học & nội dung bài học' : 'Thông tin tài liệu độc lập' }}
              </h2>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs">
              <div><span class="text-muted">Loại / Mã:</span><p class="font-semibold text-navy">{{ detail.loaiDoiTuong }} #{{ detail.maDoiTuong }}</p></div>
              <div><span class="text-muted">Vòng kiểm duyệt:</span><p class="font-semibold text-navy">Vòng {{ detail.soVongKiemDuyet }}</p></div>
              <div><span class="text-muted">Hạn tiếp nhận:</span><p class="font-medium text-ink tabular-nums">{{ formatDateTimeVi(detail.hanTiepNhan) }}</p></div>
              <div><span class="text-muted">Hạn kiểm duyệt:</span><p class="font-medium text-ink tabular-nums">{{ formatDateTimeVi(detail.hanKiemDuyet) }}</p></div>
            </div>

            <div v-if="content" class="space-y-4 pt-2 border-t border-border/70 text-sm">
              <div v-if="content.moTa">
                <p class="text-xs font-semibold text-muted uppercase">Mô tả</p>
                <p class="mt-1 whitespace-pre-line text-slate-700">{{ content.moTa }}</p>
              </div>

              <!-- Course Lessons -->
              <div v-if="isCourse && Array.isArray(content.baiHocs)" class="space-y-2.5">
                <p class="text-xs font-semibold text-muted uppercase">Danh sách bài học ({{ content.baiHocs.length }})</p>
                <div
                  v-for="(lesson, idx) in content.baiHocs"
                  :key="lesson.maBaiHoc || idx"
                  class="rounded-lg border border-border bg-canvas p-3.5 space-y-1"
                >
                  <p class="text-xs font-bold text-navy">{{ idx + 1 }}. {{ lesson.tieuDe || 'Bài học' }}</p>
                  <p v-if="lesson.noiDung" class="text-xs leading-relaxed text-slate-600 whitespace-pre-line">{{ lesson.noiDung }}</p>
                </div>
              </div>

              <div v-if="isCourse && Array.isArray(content.taiLieus) && content.taiLieus.length" class="space-y-2.5">
                <p class="text-xs font-semibold uppercase text-muted">Tệp tài liệu cần kiểm duyệt</p>
                <button
                  v-for="material in content.taiLieus"
                  :key="material.maTaiLieu"
                  type="button"
                  :disabled="openingMaterialId === String(material.maTaiLieu)"
                  class="flex w-full items-center justify-between gap-3 rounded-lg border border-border bg-canvas p-3 text-left text-xs font-semibold text-navy hover:border-teal hover:text-teal disabled:opacity-60"
                  @click="openReviewMaterial(material)"
                >
                  <span class="truncate">{{ material.tieuDe || `Tài liệu #${material.maTaiLieu}` }}</span>
                  <span>{{ openingMaterialId === String(material.maTaiLieu) ? 'Đang mở…' : 'Mở tệp' }}</span>
                </button>
              </div>

              <!-- Standalone Material URL -->
              <div v-if="!isCourse && content.duongDanTep" class="rounded-lg border border-border bg-canvas p-3.5 text-xs">
                <p class="font-semibold text-navy">Đường dẫn tệp / tài nguyên</p>
                <button
                  type="button"
                  :disabled="openingMaterialId === String(content.maTaiLieu)"
                  class="mt-2 ui-button ui-button--outline ui-button--sm"
                  @click="openReviewMaterial(content)"
                >
                  {{ openingMaterialId === String(content.maTaiLieu) ? 'Đang mở…' : 'Mở tệp được bảo vệ' }}
                </button>
              </div>
            </div>
          </section>
        </div>

        <!-- Right 5 cols: Review Decision & Draft Form -->
        <div class="space-y-4 lg:col-span-5">
          <section class="rounded-xl border border-border bg-surface p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-border/70 pb-3">
              <h2 class="text-sm font-bold text-navy">Phiếu đánh giá chuyên môn</h2>
              <span v-if="lastDraftSavedAt" class="text-[11px] text-teal font-medium">Đã lưu: {{ lastDraftSavedAt }}</span>
              <span v-else-if="isDirty" class="text-[11px] text-amber-dark font-medium">Chưa lưu bản nháp</span>
            </div>

            <div v-if="detail.trangThai === 'COMPLETED'" class="space-y-2 text-xs">
              <UiAlert variant="success" title="Nhiệm vụ đã hoàn thành" message="Kết quả kiểm duyệt đã được ghi nhận và không thể chỉnh sửa." />
              <div v-if="detail.ketQuaDanhGia" class="rounded-lg bg-subtle/60 p-3 space-y-1">
                <p><strong>Quyết định:</strong> {{ detail.ketQuaDanhGia.trangThai }}</p>
                <p v-if="detail.ketQuaDanhGia.noiDungDanhGia"><strong>Nhận xét:</strong> {{ detail.ketQuaDanhGia.noiDungDanhGia }}</p>
                <p v-if="detail.ketQuaDanhGia.ghiChu"><strong>Ghi chú:</strong> {{ detail.ketQuaDanhGia.ghiChu }}</p>
              </div>
            </div>

            <form v-else-if="canEditReview" class="space-y-3.5 text-xs" @submit.prevent="requestDecisionSubmit">
              <label class="block font-semibold text-navy">
                Quyết định kiểm duyệt <span class="text-danger">*</span>
                <select v-model="form.trangThai" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink focus:border-teal focus:outline-none" @change="markDirty">
                  <option value="APPROVED">Phê duyệt học thuật (APPROVED)</option>
                  <option value="NEEDS_REVISION">Yêu cầu chỉnh sửa (NEEDS_REVISION)</option>
                  <option value="REJECTED">Từ chối nội dung (REJECTED)</option>
                </select>
              </label>

              <div class="grid grid-cols-2 gap-3">
                <label class="block font-semibold text-navy">
                  Điểm kỹ thuật (0–10)
                  <input v-model="form.diemKyThuat" type="number" step="0.5" min="0" max="10" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs tabular-nums focus:border-teal focus:outline-none" @input="markDirty" />
                </label>
                <label class="block font-semibold text-navy">
                  Điểm nội dung (0–10)
                  <input v-model="form.diemNoiDung" type="number" step="0.5" min="0" max="10" class="mt-1.5 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs tabular-nums focus:border-teal focus:outline-none" @input="markDirty" />
                </label>
              </div>

              <label class="block font-semibold text-navy">
                Nội dung đánh giá chuyên môn
                <textarea v-model="form.noiDungDanhGia" rows="4" placeholder="Nhận xét về cấu trúc, độ chính xác học thuật, tài liệu đính kèm..." class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none" @input="markDirty" />
              </label>

              <label class="block font-semibold text-navy">
                Ghi chú gửi Nhà cung cấp <span v-if="form.trangThai !== 'APPROVED'" class="text-danger">*</span>
                <textarea v-model="form.ghiChu" rows="3" placeholder="Bắt buộc nêu rõ điểm cần sửa nếu từ chối hoặc yêu cầu chỉnh sửa..." class="mt-1.5 w-full rounded-lg border border-border bg-canvas p-2.5 text-xs text-ink focus:border-teal focus:outline-none" @input="markDirty" />
              </label>

              <p class="text-[11px] leading-relaxed text-muted">
                Lưu ý: Phê duyệt học thuật không tự động công khai khóa học; quyền xuất bản thuộc phạm vi hiển thị theo quy trình hệ thống.
              </p>

              <div class="flex flex-wrap items-center justify-between gap-2 pt-2">
                <button
                  type="button"
                  class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle disabled:opacity-50"
                  :disabled="savingDraft"
                  @click="handleSaveDraft"
                >
                  <Save :size="14" aria-hidden="true" />
                  <span>{{ savingDraft ? 'Đang lưu...' : 'Lưu bản nháp' }}</span>
                </button>

                <button
                  type="submit"
                  class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-4 py-2 text-xs font-semibold text-white hover:bg-navy/90 disabled:opacity-50"
                  :disabled="submitting"
                >
                  <Send :size="14" aria-hidden="true" />
                  <span>Gửi quyết định chính thức</span>
                </button>
              </div>
            </form>

            <p v-else class="text-xs text-muted">
              Nhiệm vụ ở trạng thái <strong>{{ detail.trangThai }}</strong> không cho phép chỉnh sửa biểu mẫu đánh giá.
            </p>
          </section>
        </div>
      </div>
    </template>

    <!-- Confirm Decision Modal -->
    <div v-if="confirmOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 p-4 backdrop-blur-[2px]">
      <div class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl" role="dialog" aria-modal="true" aria-label="Xác nhận gửi quyết định kiểm duyệt">
        <h2 class="text-base font-bold text-navy">Xác nhận gửi quyết định chính thức</h2>
        <p class="mt-2 text-xs leading-relaxed text-muted">
          Quyết định: <strong class="text-navy">{{ form.trangThai }}</strong>. Sau khi gửi, nhiệm vụ sẽ chuyển sang <code>COMPLETED</code> và không thể chỉnh sửa lại.
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-navy hover:bg-subtle" :disabled="submitting" @click="confirmOpen = false">
            Xem lại
          </button>
          <button type="button" class="rounded-lg bg-teal px-4 py-2 text-xs font-semibold text-white hover:bg-teal-dark disabled:opacity-50" :disabled="submitting" @click="confirmDecisionSubmit">
            {{ submitting ? 'Đang gửi...' : 'Xác nhận gửi' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
