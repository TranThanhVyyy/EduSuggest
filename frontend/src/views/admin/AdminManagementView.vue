<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  Check,
  Copy,
  Edit3,
  KeyRound,
  Lock,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  Unlock,
  UserCheck,
  UserPlus,
  X,
} from 'lucide-vue-next'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import api from '@/service/api'

const route = useRoute()
const resource = computed(() => route.meta.adminResource)

const titles = {
  users: 'Tài khoản người học',
  reviewers: 'Tài khoản chuyên gia',
  providers: 'Tài khoản nhà cung cấp',
  categories: 'Danh mục khóa học',
  courses: 'Danh sách khóa học',
  materials: 'Tài liệu học tập',
}

const subtitles = {
  users: 'Quản lý danh sách tài khoản học viên (USER), cấp vai trò chuyên gia, khóa hoặc xóa tài khoản.',
  reviewers: 'Quản lý tài khoản chuyên gia kiểm duyệt do quản trị viên cấp, hỗ trợ cấp lại mật khẩu, khóa hoặc xóa.',
  providers: 'Quản lý tài khoản nhà cung cấp đào tạo, hỗ trợ khóa hoặc xóa tài khoản.',
  categories: 'Tạo mới, chỉnh sửa và chuẩn hóa nhóm ngành đào tạo trên hệ thống.',
  courses: 'Tra cứu toàn bộ khóa học và trạng thái kiểm duyệt, hiển thị.',
  materials: 'Quản lý tài liệu học tập và trạng thái hiển thị công khai.',
}

const title = computed(() => titles[resource.value] || 'Quản lý dữ liệu')
const subtitle = computed(() => subtitles[resource.value] || 'Quản trị thông tin và điều phối tài nguyên hệ thống.')

const isUserResource = computed(() => ['users', 'reviewers', 'providers'].includes(resource.value))
const isServerPaginated = computed(() => resource.value === 'materials')
const canEditCategories = computed(() => resource.value === 'categories')

const rows = ref([])
const loading = ref(true)
const saving = ref(false)
const busyUserId = ref(null)
const errorMessage = ref('')
const successMessage = ref('')

// Category Editor Modal
const editorOpen = ref(false)
const editingId = ref(null)
const form = reactive({ tenDanhMuc: '', moTa: '' })

// User Action Confirmation Modal (lock / unlock / delete / grant-expert)
const userModal = reactive({
  open: false,
  type: '',
  user: null,
  submitting: false,
})

// Expert Password Reset Modal
const resetModal = reactive({
  open: false,
  user: null,
  customPassword: '',
  generatedPassword: '',
  copied: false,
  submitting: false,
  error: '',
})

// Create Expert Account Modal
const createExpertModal = reactive({
  open: false,
  tenTaiKhoan: '',
  hoTen: '',
  email: '',
  soDienThoai: '',
  matKhauTamThoi: '',
  createdResult: null,
  copied: false,
  submitting: false,
  error: '',
})

// Verify Expert Profile Modal
const verifyModal = reactive({
  open: false,
  expert: null,
  decision: 'VERIFIED',
  note: '',
  submitting: false,
  error: '',
})

// Search & Filter state
const searchQuery = ref('')
const selectedFilter = ref('')

// Server-side pagination state (used for materials)
const currentPage = ref(1)
const pageSize = 20
const totalItems = ref(0)
const totalPages = ref(0)
let searchTimer = null

const columns = computed(() => {
  if (resource.value === 'categories') {
    return [
      { key: 'tenDanhMuc', label: 'Tên danh mục' },
      { key: 'moTa', label: 'Mô tả chi tiết' },
    ]
  }
  if (resource.value === 'courses') {
    return [
      { key: 'tieuDe', label: 'Tên khóa học' },
      { key: 'trangThaiDuyet', label: 'Kiểm duyệt' },
      { key: 'trangThaiHienThi', label: 'Hiển thị' },
    ]
  }
  if (resource.value === 'materials') {
    return [
      { key: 'tieuDe', label: 'Tên tài liệu' },
      { key: 'loai', label: 'Định dạng' },
      { key: 'trangThaiDuyet', label: 'Kiểm duyệt' },
      { key: 'trangThaiHienThi', label: 'Hiển thị' },
    ]
  }
  if (resource.value === 'reviewers') {
    return [
      { key: 'hoTen', label: 'Chuyên gia' },
      { key: 'chuyenMon', label: 'Chuyên môn' },
      { key: 'trangThai', label: 'Trạng thái' },
    ]
  }
  return [
    { key: 'hoTen', label: 'Họ và tên' },
    { key: 'email', label: 'Email' },
    { key: 'trangThai', label: 'Trạng thái' },
  ]
})

function unwrapResponseError(error, fallback) {
  return error.response?.data?.detail || fallback
}

async function loadRows({ resetFilters = false } = {}) {
  loading.value = true
  errorMessage.value = ''
  if (resetFilters) {
    successMessage.value = ''
    searchQuery.value = ''
    selectedFilter.value = ''
    currentPage.value = 1
  }

  try {
    if (resource.value === 'categories') {
      const { data } = await api.get('/admin/categories')
      rows.value = data
      totalItems.value = data.length
      totalPages.value = data.length ? 1 : 0
    } else if (resource.value === 'courses') {
      const { data } = await api.get('/admin/courses')
      rows.value = data
      totalItems.value = data.length
      totalPages.value = data.length ? 1 : 0
    } else if (resource.value === 'reviewers') {
      const { data } = await api.get('/admin/experts')
      rows.value = data
      totalItems.value = data.length
      totalPages.value = data.length ? 1 : 0
    } else if (isUserResource.value) {
      const { data } = await api.get('/admin/users')
      const targetRole = resource.value === 'users' ? 'USER' : 'PROVIDER'
      rows.value = data.filter((user) => user.tenVaiTro === targetRole)
      totalItems.value = rows.value.length
      totalPages.value = rows.value.length ? 1 : 0
    } else if (resource.value === 'materials') {
      const params = { page: currentPage.value, page_size: pageSize }
      if (searchQuery.value.trim()) params.query = searchQuery.value.trim()
      if (selectedFilter.value) params.status = selectedFilter.value
      const { data } = await api.get('/admin/materials', { params })
      const items = Array.isArray(data) ? data : (data.items || [])
      const total = Array.isArray(data) ? data.length : Number(data.total ?? 0)
      const pages = Array.isArray(data) ? (data.length ? 1 : 0) : Number(data.total_pages ?? 0)
      if (pages > 0 && currentPage.value > pages) {
        currentPage.value = pages
        return
      }
      rows.value = items
      totalItems.value = total
      totalPages.value = pages
    } else {
      rows.value = []
      totalItems.value = 0
      totalPages.value = 0
    }
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, `Không thể tải dữ liệu ${title.value.toLocaleLowerCase('vi')}.`)
  } finally {
    loading.value = false
  }
}

const filteredRows = computed(() => {
  if (isServerPaginated.value) return rows.value
  return rows.value.filter((row) => {
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.trim().toLowerCase()
      const matches = Object.values(row).some((val) =>
        String(val || '').toLowerCase().includes(query),
      )
      if (!matches) return false
    }
    if (selectedFilter.value) {
      if (isUserResource.value && (row.trangThai || 'ACTIVE') !== selectedFilter.value) {
        return false
      }
      if (resource.value === 'courses' && row.trangThaiDuyet !== selectedFilter.value) {
        return false
      }
    }
    return true
  })
})

function openCreate() {
  editingId.value = null
  Object.assign(form, { tenDanhMuc: '', moTa: '' })
  editorOpen.value = true
}

function openEdit(row) {
  editingId.value = row.maDanhMuc
  Object.assign(form, { tenDanhMuc: row.tenDanhMuc || '', moTa: row.moTa || '' })
  editorOpen.value = true
}

async function saveCategory() {
  if (saving.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    const payload = { tenDanhMuc: form.tenDanhMuc.trim(), moTa: form.moTa.trim() || null }
    const wasEditing = editingId.value !== null
    if (wasEditing) await api.patch(`/admin/categories/${editingId.value}`, payload)
    else await api.post('/admin/categories', payload)
    editorOpen.value = false
    await loadRows()
    successMessage.value = wasEditing ? 'Danh mục đã được cập nhật thành công.' : 'Danh mục mới đã được tạo thành công.'
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, 'Không thể lưu danh mục.')
  } finally {
    saving.value = false
  }
}

async function deleteCategory(row) {
  if (!window.confirm(`Bạn có chắc chắn muốn xóa danh mục “${row.tenDanhMuc}”?`)) return
  errorMessage.value = ''
  try {
    await api.delete(`/admin/categories/${row.maDanhMuc}`)
    await loadRows()
    successMessage.value = 'Danh mục đã được xóa thành công.'
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, 'Không thể xóa danh mục. Có thể danh mục đang có khóa học liên kết.')
  }
}

function askUserAction(type, user) {
  userModal.type = type
  userModal.user = user
  userModal.open = true
}

async function confirmUserAction() {
  const user = userModal.user
  if (!user || userModal.submitting) return
  userModal.submitting = true
  busyUserId.value = user.maNguoiDung
  errorMessage.value = ''
  successMessage.value = ''

  try {
    if (userModal.type === 'grant-expert') {
      const { data } = await api.post(`/admin/users/${user.maNguoiDung}/expert-role`, {})
      rows.value = rows.value.filter((row) => row.maNguoiDung !== data.maNguoiDung)
      successMessage.value = `Đã cấp vai trò Chuyên gia cho ${data.hoTen || data.email}. Tài khoản đã chuyển sang mục Chuyên gia.`
    } else if (userModal.type === 'lock' || userModal.type === 'unlock') {
      const nextStatus = userModal.type === 'lock' ? 'LOCKED' : 'ACTIVE'
      const { data } = await api.patch(`/admin/users/${user.maNguoiDung}/status`, {
        trangThai: nextStatus,
      })
      rows.value = rows.value.map((row) => (row.maNguoiDung === data.maNguoiDung ? data : row))
      successMessage.value =
        nextStatus === 'LOCKED'
          ? `Đã khóa tài khoản ${data.hoTen || data.tenTaiKhoan}.`
          : `Đã mở khóa tài khoản ${data.hoTen || data.tenTaiKhoan}.`
    } else if (userModal.type === 'delete') {
      await api.delete(`/admin/users/${user.maNguoiDung}`)
      rows.value = rows.value.filter((row) => row.maNguoiDung !== user.maNguoiDung)
      successMessage.value = `Đã xóa tài khoản ${user.hoTen || user.tenTaiKhoan}.`
    }
    userModal.open = false
    userModal.user = null
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, 'Không thể thực hiện thao tác trên tài khoản.')
    userModal.open = false
  } finally {
    userModal.submitting = false
    busyUserId.value = null
  }
}

function openResetPasswordModal(user) {
  resetModal.user = user
  resetModal.customPassword = ''
  resetModal.generatedPassword = ''
  resetModal.copied = false
  resetModal.error = ''
  resetModal.open = true
}

async function submitResetPassword() {
  if (!resetModal.user || resetModal.submitting) return
  const custom = resetModal.customPassword.trim()
  if (custom && custom.length < 8) {
    resetModal.error = 'Mật khẩu mới phải có ít nhất 8 ký tự.'
    return
  }
  resetModal.submitting = true
  resetModal.error = ''
  try {
    const payload = custom ? { matKhauMoi: custom } : {}
    const { data } = await api.post(`/admin/experts/${resetModal.user.maNguoiDung}/reset-password`, payload)
    resetModal.generatedPassword = data.matKhauMoi
    successMessage.value = `Đã cấp lại mật khẩu mới cho chuyên gia ${resetModal.user.hoTen || resetModal.user.tenTaiKhoan}.`
  } catch (error) {
    resetModal.error = unwrapResponseError(error, 'Không thể cấp lại mật khẩu cho chuyên gia.')
  } finally {
    resetModal.submitting = false
  }
}

async function copyGeneratedPassword() {
  if (!resetModal.generatedPassword) return
  try {
    await navigator.clipboard.writeText(resetModal.generatedPassword)
    resetModal.copied = true
    setTimeout(() => { resetModal.copied = false }, 2000)
  } catch {
    resetModal.copied = false
  }
}

function openCreateExpertModal() {
  Object.assign(createExpertModal, {
    open: true,
    tenTaiKhoan: '',
    hoTen: '',
    email: '',
    soDienThoai: '',
    matKhauTamThoi: '',
    createdResult: null,
    copied: false,
    submitting: false,
    error: '',
  })
}

async function submitCreateExpert() {
  if (createExpertModal.submitting) return
  createExpertModal.submitting = true
  createExpertModal.error = ''
  try {
    const payload = {
      tenTaiKhoan: createExpertModal.tenTaiKhoan.trim(),
      hoTen: createExpertModal.hoTen.trim(),
      email: createExpertModal.email.trim(),
      soDienThoai: createExpertModal.soDienThoai.trim() || null,
    }
    if (createExpertModal.matKhauTamThoi.trim()) {
      payload.matKhauTamThoi = createExpertModal.matKhauTamThoi.trim()
    }
    const { data } = await api.post('/admin/experts', payload)
    createExpertModal.createdResult = data
    successMessage.value = `Đã tạo tài khoản Chuyên gia @${data.tenTaiKhoan}.`
    await loadRows()
  } catch (error) {
    createExpertModal.error = unwrapResponseError(error, 'Không thể tạo tài khoản chuyên gia.')
  } finally {
    createExpertModal.submitting = false
  }
}

async function copyCreatedExpertPassword() {
  const pwd = createExpertModal.createdResult?.matKhauTamThoi
  if (!pwd) return
  try {
    await navigator.clipboard.writeText(pwd)
    createExpertModal.copied = true
    setTimeout(() => { createExpertModal.copied = false }, 2000)
  } catch {
    createExpertModal.copied = false
  }
}

function openVerifyModal(expert) {
  verifyModal.expert = expert
  verifyModal.decision = expert.trangThaiHoSo === 'VERIFIED' ? 'VERIFIED' : 'VERIFIED'
  verifyModal.note = expert.ghiChuXacMinh || ''
  verifyModal.error = ''
  verifyModal.submitting = false
  verifyModal.open = true
}

async function submitExpertVerification() {
  if (!verifyModal.expert || verifyModal.submitting) return
  if (verifyModal.decision === 'NEEDS_UPDATE' && !verifyModal.note.trim()) {
    verifyModal.error = 'Vui lòng nhập ghi chú yêu cầu bổ sung cho chuyên gia.'
    return
  }
  verifyModal.submitting = true
  verifyModal.error = ''
  try {
    const { data } = await api.patch(
      `/admin/experts/${verifyModal.expert.maNguoiDung}/verification`,
      {
        trangThaiHoSo: verifyModal.decision,
        ghiChuXacMinh: verifyModal.note.trim() || null,
      },
    )
    rows.value = rows.value.map((r) => (r.maNguoiDung === data.maNguoiDung ? data : r))
    successMessage.value =
      verifyModal.decision === 'VERIFIED'
        ? `Đã xác minh hồ sơ chuyên gia ${data.hoTen || data.tenTaiKhoan}.`
        : `Đã gửi yêu cầu bổ sung hồ sơ tới ${data.hoTen || data.tenTaiKhoan}.`
    verifyModal.open = false
  } catch (error) {
    verifyModal.error = unwrapResponseError(error, 'Không thể cập nhật trạng thái xác minh hồ sơ.')
  } finally {
    verifyModal.submitting = false
  }
}

function profileStatusBadge(status) {
  if (status === 'VERIFIED') return { label: 'Đã xác minh', cls: 'bg-teal/10 text-teal-dark border-teal/25' }
  if (status === 'PENDING_VERIFICATION') return { label: 'Chờ xác minh', cls: 'bg-amber/10 text-amber border-amber/25' }
  if (status === 'NEEDS_UPDATE') return { label: 'Cần bổ sung', cls: 'bg-rose-50 text-danger border-rose-200' }
  return { label: 'Bản nháp', cls: 'bg-slate-100 text-slate-600 border-slate-200' }
}

async function toggleMaterialVisibility(row) {
  const newVisibility = row.trangThaiHienThi === 'VISIBLE' ? 'HIDDEN' : 'VISIBLE'
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const { data } = await api.patch(`/admin/materials/${row.maTaiLieu}`, {
      trangThaiHienThi: newVisibility,
    })
    row.trangThaiHienThi = data.trangThaiHienThi
    successMessage.value = `Đã cập nhật trạng thái hiển thị tài liệu #${row.maTaiLieu}.`
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, 'Không thể cập nhật trạng thái hiển thị.')
  }
}

function handleEscape(event) {
  if (event.key === 'Escape') {
    if (editorOpen.value) editorOpen.value = false
    if (userModal.open) userModal.open = false
    if (resetModal.open) resetModal.open = false
    if (createExpertModal.open) createExpertModal.open = false
    if (verifyModal.open) verifyModal.open = false
  }
}

watch(resource, () => loadRows({ resetFilters: true }))
watch(currentPage, () => {
  if (isServerPaginated.value) loadRows()
})
watch(selectedFilter, () => {
  if (!isServerPaginated.value) return
  if (currentPage.value !== 1) currentPage.value = 1
  else loadRows()
})
watch(searchQuery, () => {
  if (!isServerPaginated.value) return
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (currentPage.value !== 1) currentPage.value = 1
    else loadRows()
  }, 250)
})

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
  loadRows({ resetFilters: true })
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleEscape)
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header with Actions -->
    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Quản trị hệ thống</p>
        <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">{{ title }}</h1>
        <p class="mt-1.5 text-sm text-slate-600">{{ subtitle }}</p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 shrink-0">
        <UiButton
          v-if="canEditCategories"
          variant="primary"
          size="sm"
          @click="openCreate"
        >
          <Plus :size="15" aria-hidden="true" />
          <span>Tạo danh mục mới</span>
        </UiButton>

        <UiButton
          v-if="resource === 'reviewers'"
          variant="primary"
          size="sm"
          @click="openCreateExpertModal"
        >
          <UserPlus :size="15" aria-hidden="true" />
          <span>Tạo tài khoản chuyên gia</span>
        </UiButton>

        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          :disabled="loading"
          @click="loadRows"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </header>

    <!-- Feedback Alerts -->
    <UiAlert
      v-if="errorMessage"
      variant="danger"
      :message="errorMessage"
      dismissible
      @dismiss="errorMessage = ''"
    />

    <UiAlert
      v-if="successMessage"
      variant="success"
      :message="successMessage"
      dismissible
      @dismiss="successMessage = ''"
    />

    <!-- Search & Filter Controls -->
    <div
      v-if="!loading && (rows.length || searchQuery || selectedFilter)"
      class="flex flex-col justify-between gap-3 rounded-2xl border border-border bg-surface px-4 py-3.5 sm:flex-row sm:items-center"
    >
      <div class="flex flex-1 flex-wrap items-center gap-3">
        <div class="relative min-w-[220px] max-w-sm flex-1">
          <Search :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Tìm kiếm theo tên, email, tài khoản..."
            class="ui-input h-9 pl-9 text-xs"
          >
        </div>

        <select
          v-if="isUserResource"
          v-model="selectedFilter"
          class="ui-input h-9 w-44 text-xs"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="ACTIVE">Đang hoạt động</option>
          <option value="LOCKED">Đã khóa</option>
        </select>

        <select
          v-else-if="resource === 'materials'"
          v-model="selectedFilter"
          class="ui-input h-9 w-44 text-xs"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="APPROVED">Đã phê duyệt</option>
          <option value="PENDING">Chờ kiểm duyệt</option>
          <option value="DRAFT">Bản nháp</option>
          <option value="REJECTED">Bị từ chối</option>
          <option value="NEEDS_REVISION">Cần chỉnh sửa</option>
        </select>
      </div>

      <div class="flex items-center gap-2 text-xs text-slate-500">
        <span class="tabular-nums">{{ filteredRows.length }} / {{ isServerPaginated ? totalItems : rows.length }} bản ghi</span>
        <button
          v-if="searchQuery || selectedFilter"
          type="button"
          class="ml-1 inline-flex items-center gap-1 font-semibold text-teal hover:underline"
          @click="searchQuery = ''; selectedFilter = ''; currentPage = 1"
        >
          <X :size="12" aria-hidden="true" />
          <span>Xóa lọc</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="rounded-2xl border border-border bg-surface p-5">
      <UiSkeleton variant="table" :lines="6" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!rows.length" class="rounded-2xl border border-border bg-surface p-6">
      <UiEmptyState
        title="Chưa có dữ liệu"
        :description="resource === 'providers'
          ? 'Chưa có tài khoản nhà cung cấp nào được phê duyệt.'
          : resource === 'reviewers'
            ? 'Chưa có tài khoản chuyên gia nào. Bạn có thể cấp quyền Chuyên gia từ mục Tài khoản.'
            : 'Hệ thống chưa ghi nhận bản ghi nào trong mục này.'
        "
        :action-label="canEditCategories ? 'Tạo danh mục đầu tiên' : ''"
        @action="openCreate"
      />
    </div>

    <!-- Data Table -->
    <div v-else class="overflow-hidden rounded-2xl border border-border bg-surface shadow-xs">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] text-left text-sm">
          <thead class="border-b border-border/80 bg-background text-[11px] font-semibold uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th
                v-for="column in columns"
                :key="column.key"
                class="whitespace-nowrap px-5 py-3"
              >
                {{ column.label }}
              </th>
              <th
                v-if="canEditCategories || isUserResource || resource === 'materials'"
                class="whitespace-nowrap px-5 py-3 text-center"
              >
                Thao tác
              </th>
            </tr>
          </thead>

          <tbody class="divide-y divide-border/60">
            <tr
              v-for="row in filteredRows"
              :key="row.maDanhMuc || row.maNguoiDung || row.maKhoaHoc || row.maTaiLieu"
              class="align-middle transition-colors duration-150 hover:bg-background/70"
            >
              <td
                v-for="column in columns"
                :key="column.key"
                class="px-5 py-3.5 text-sm text-navy"
              >
                <template v-if="['trangThaiDuyet', 'trangThaiHienThi'].includes(column.key)">
                  <UiStatusBadge :status="row[column.key]" />
                </template>

                <template v-else-if="column.key === 'hoTen' && isUserResource">
                  <div class="font-semibold text-navy">{{ row.hoTen || 'Chưa cập nhật tên' }}</div>
                  <div class="mt-0.5 text-xs text-slate-500">
                    @{{ row.tenTaiKhoan || `user-${row.maNguoiDung}` }}
                    <span v-if="row.soDienThoai"> · {{ row.soDienThoai }}</span>
                  </div>
                </template>

                <template v-else-if="column.key === 'chuyenMon' && resource === 'reviewers'">
                  <div class="max-w-xs space-y-1">
                    <div v-if="row.primarySpecialty" class="flex flex-wrap items-center gap-1.5">
                      <span class="rounded-md bg-teal/10 px-2 py-0.5 text-xs font-semibold text-teal-dark">
                        Chính: {{ row.primarySpecialty.tenChuyenMon }}
                      </span>
                      <span
                        v-if="row.secondarySpecialties?.length"
                        class="rounded-md bg-subtle px-2 py-0.5 text-[11px] font-medium text-slate-600"
                      >
                        +{{ row.secondarySpecialties.length }} phụ
                      </span>
                    </div>
                    <div v-else class="break-words text-xs text-slate-500">
                      {{ row.chuyenMon ? `Cũ: ${row.chuyenMon}` : 'Chưa chọn chuyên môn' }}
                    </div>
                    <div class="flex flex-wrap items-center gap-1.5">
                      <span
                        class="inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold"
                        :class="profileStatusBadge(row.trangThaiHoSo).cls"
                      >
                        {{ profileStatusBadge(row.trangThaiHoSo).label }}
                      </span>
                      <span
                        v-if="row.soNamKinhNghiem !== null && row.soNamKinhNghiem !== undefined"
                        class="text-[11px] text-slate-500"
                      >
                        {{ row.soNamKinhNghiem }} năm KN
                      </span>
                      <span
                        v-if="row.batBuocDoiMatKhau"
                        class="rounded-full bg-amber/10 px-2 py-0.5 text-[10px] font-semibold text-amber"
                      >
                        Chưa đổi MK lần đầu
                      </span>
                    </div>
                  </div>
                </template>

                <template v-else-if="column.key === 'trangThai' && isUserResource">
                  <span
                    class="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold"
                    :class="(row.trangThai || 'ACTIVE') === 'LOCKED'
                      ? 'bg-rose-50 text-danger border border-rose-200'
                      : 'bg-teal/10 text-teal-dark border border-teal/20'"
                  >
                    <span
                      class="size-1.5 rounded-full"
                      :class="(row.trangThai || 'ACTIVE') === 'LOCKED' ? 'bg-danger' : 'bg-teal'"
                      aria-hidden="true"
                    ></span>
                    <span>{{ (row.trangThai || 'ACTIVE') === 'LOCKED' ? 'Đã khóa' : 'Hoạt động' }}</span>
                  </span>
                </template>

                <template v-else>
                  <span class="font-medium">{{ row[column.key] || '—' }}</span>
                </template>
              </td>

              <!-- Category Actions -->
              <td v-if="canEditCategories" class="whitespace-nowrap px-5 py-3.5 text-center">
                <div class="inline-flex items-center justify-center gap-2">
                  <button
                    type="button"
                    class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy transition-colors hover:border-teal/50 hover:text-teal"
                    @click="openEdit(row)"
                  >
                    <Edit3 :size="13" aria-hidden="true" />
                    <span>Sửa</span>
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-danger transition-colors hover:border-danger/40 hover:bg-danger/5"
                    :aria-label="`Xóa ${row.tenDanhMuc}`"
                    @click="deleteCategory(row)"
                  >
                    <Trash2 :size="13" aria-hidden="true" />
                    <span>Xóa</span>
                  </button>
                </div>
              </td>

              <!-- User / Expert / Provider Actions -->
              <td v-else-if="isUserResource" class="whitespace-nowrap px-5 py-3.5 text-center">
                <div class="inline-flex flex-nowrap items-center justify-center gap-1.5">
                  <!-- Only on USER table: Grant EXPERT -->
                  <button
                    v-if="resource === 'users'"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-2.5 text-xs font-semibold text-navy transition-colors hover:border-teal/50 hover:text-teal disabled:opacity-50"
                    :disabled="busyUserId !== null"
                    @click="askUserAction('grant-expert', row)"
                  >
                    <UserCheck :size="13" class="text-teal" aria-hidden="true" />
                    <span>Cấp chuyên gia</span>
                  </button>

                  <!-- Only on EXPERT table: Verify Profile & Reset Password -->
                  <button
                    v-if="resource === 'reviewers'"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-teal/35 bg-teal/5 px-2.5 text-xs font-semibold text-teal-dark transition-colors hover:bg-teal/10 disabled:opacity-50"
                    :disabled="busyUserId !== null"
                    @click="openVerifyModal(row)"
                  >
                    <ShieldCheck :size="13" aria-hidden="true" />
                    <span>Xác minh</span>
                  </button>

                  <button
                    v-if="resource === 'reviewers'"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal px-3 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(13,148,136,0.22)] transition-colors hover:bg-teal-dark disabled:opacity-50"
                    :disabled="busyUserId !== null"
                    @click="openResetPasswordModal(row)"
                  >
                    <KeyRound :size="13" aria-hidden="true" />
                    <span>Cấp lại mật khẩu</span>
                  </button>

                  <!-- Lock / Unlock (all 3 user tables) -->
                  <button
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-2.5 text-xs font-semibold transition-colors disabled:opacity-50"
                    :class="(row.trangThai || 'ACTIVE') === 'LOCKED'
                      ? 'text-teal-dark hover:border-teal/50 hover:bg-teal/5'
                      : 'text-amber hover:border-amber/50 hover:bg-amber/5'"
                    :disabled="busyUserId !== null"
                    @click="askUserAction((row.trangThai || 'ACTIVE') === 'LOCKED' ? 'unlock' : 'lock', row)"
                  >
                    <Unlock v-if="(row.trangThai || 'ACTIVE') === 'LOCKED'" :size="13" aria-hidden="true" />
                    <Lock v-else :size="13" aria-hidden="true" />
                    <span>{{ (row.trangThai || 'ACTIVE') === 'LOCKED' ? 'Mở khóa' : 'Khóa' }}</span>
                  </button>

                  <!-- Delete (all 3 user tables) -->
                  <button
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-lg border border-border bg-surface px-2.5 text-xs font-semibold text-danger transition-colors hover:border-danger/40 hover:bg-danger/5 disabled:opacity-50"
                    :disabled="busyUserId !== null"
                    @click="askUserAction('delete', row)"
                  >
                    <Trash2 :size="13" aria-hidden="true" />
                    <span>Xóa</span>
                  </button>
                </div>
              </td>

              <!-- Material Actions -->
              <td v-else-if="resource === 'materials'" class="whitespace-nowrap px-5 py-3.5 text-center">
                <button
                  v-if="row.trangThaiDuyet === 'APPROVED'"
                  type="button"
                  class="inline-flex h-8 items-center rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-teal-dark transition-colors hover:border-teal/50 hover:bg-teal/5"
                  @click="toggleMaterialVisibility(row)"
                >
                  {{ row.trangThaiHienThi === 'VISIBLE' ? 'Ẩn tài liệu' : 'Hiện tài liệu' }}
                </button>
                <span v-else class="text-xs text-slate-400">Chưa duyệt</span>
              </td>
            </tr>

            <tr v-if="!filteredRows.length">
              <td :colspan="columns.length + 1" class="py-8 text-center text-xs text-slate-500">
                Không tìm thấy bản ghi nào khớp với bộ lọc hiện tại.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <PaginationControls
        v-if="isServerPaginated && totalPages > 1"
        v-model="currentPage"
        :total-pages="totalPages"
        :total-items="totalItems"
      />
    </div>

    <!-- Category Editor Modal -->
    <Transition name="es-fade">
      <div
        v-if="editorOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
        @click.self="editorOpen = false"
      >
        <section
          class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-5"
          role="dialog"
          aria-modal="true"
          aria-labelledby="category-editor-title"
        >
          <header class="flex items-start justify-between border-b border-border/70 pb-3.5">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.08em] text-teal-dark">Danh mục đào tạo</p>
              <h2 id="category-editor-title" class="mt-0.5 font-display text-lg font-bold text-navy">
                {{ editingId ? 'Chỉnh sửa danh mục' : 'Thêm danh mục mới' }}
              </h2>
            </div>
            <button
              type="button"
              aria-label="Đóng"
              class="rounded-lg p-1.5 text-slate-400 hover:bg-subtle hover:text-navy"
              @click="editorOpen = false"
            >
              <X :size="18" aria-hidden="true" />
            </button>
          </header>

          <form class="space-y-4" @submit.prevent="saveCategory">
            <label class="block text-xs font-semibold text-navy">
              Tên danh mục <span class="text-danger">*</span>
              <input
                v-model.trim="form.tenDanhMuc"
                class="ui-input mt-1.5"
                placeholder="VD: Lập trình Web, Trí tuệ nhân tạo..."
                maxlength="255"
                required
              >
            </label>

            <label class="block text-xs font-semibold text-navy">
              Mô tả tóm tắt
              <textarea
                v-model.trim="form.moTa"
                class="ui-input mt-1.5 min-h-24"
                rows="3"
                placeholder="Mô tả phạm vi và mục tiêu kiến thức của danh mục..."
              />
            </label>

            <div class="flex justify-end gap-2 border-t border-border/70 pt-4">
              <button type="button" class="ui-button ui-button--outline ui-button--sm" @click="editorOpen = false">
                Hủy
              </button>
              <UiButton type="submit" variant="primary" size="sm" :loading="saving">
                <Save :size="14" aria-hidden="true" />
                <span>Lưu danh mục</span>
              </UiButton>
            </div>
          </form>
        </section>
      </div>
    </Transition>

    <!-- User Lock / Unlock / Delete / Grant Expert Confirmation Modal -->
    <Transition name="es-fade">
      <div
        v-if="userModal.open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
        @click.self="userModal.open = false"
      >
        <section
          class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4"
          role="dialog"
          aria-modal="true"
        >
          <h2 class="font-display text-lg font-bold text-navy">
            <template v-if="userModal.type === 'lock'">Xác nhận khóa tài khoản</template>
            <template v-else-if="userModal.type === 'unlock'">Xác nhận mở khóa tài khoản</template>
            <template v-else-if="userModal.type === 'delete'">Xác nhận xóa tài khoản</template>
            <template v-else>Cấp quyền Chuyên gia kiểm duyệt</template>
          </h2>

          <p class="text-sm leading-relaxed text-slate-600">
            <template v-if="userModal.type === 'lock'">
              Tài khoản <strong class="text-navy">{{ userModal.user?.hoTen || userModal.user?.tenTaiKhoan }}</strong> sẽ bị khóa ngay lập tức và không thể đăng nhập cho đến khi quản trị viên mở khóa.
            </template>
            <template v-else-if="userModal.type === 'unlock'">
              Mở khóa lại tài khoản <strong class="text-navy">{{ userModal.user?.hoTen || userModal.user?.tenTaiKhoan }}</strong> để người dùng có thể đăng nhập bình thường.
            </template>
            <template v-else-if="userModal.type === 'delete'">
              Xóa vĩnh viễn tài khoản <strong class="text-navy">{{ userModal.user?.hoTen || userModal.user?.tenTaiKhoan }}</strong>. Lưu ý: nếu tài khoản đã có dữ liệu khóa học, học tập hoặc kiểm duyệt, hệ thống sẽ từ chối xóa để bảo toàn dữ liệu.
            </template>
            <template v-else>
              Nâng cấp tài khoản <strong class="text-navy">{{ userModal.user?.hoTen || userModal.user?.tenTaiKhoan }}</strong> lên vai trò <strong>Chuyên gia (EXPERT)</strong> để có quyền kiểm duyệt khóa học và tài liệu.
            </template>
          </p>

          <footer class="flex justify-end gap-2 border-t border-border/70 pt-4">
            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm"
              :disabled="userModal.submitting"
              @click="userModal.open = false"
            >
              Hủy
            </button>
            <button
              type="button"
              class="ui-button ui-button--sm"
              :class="userModal.type === 'delete' ? 'bg-danger text-white hover:opacity-90' : 'ui-button--primary'"
              :disabled="userModal.submitting"
              @click="confirmUserAction"
            >
              {{ userModal.submitting ? 'Đang xử lý…' : 'Xác nhận' }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>

    <!-- Expert Reset Password Modal -->
    <Transition name="es-fade">
      <div
        v-if="resetModal.open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
        @click.self="resetModal.open = false"
      >
        <section
          class="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reset-password-title"
        >
          <header class="flex items-start justify-between gap-3 border-b border-border/70 pb-3.5">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.08em] text-teal-dark">Tài khoản chuyên gia</p>
              <h2 id="reset-password-title" class="mt-0.5 font-display text-lg font-bold text-navy">
                Cấp lại mật khẩu
              </h2>
            </div>
            <button
              type="button"
              aria-label="Đóng"
              class="rounded-lg p-1.5 text-slate-400 hover:bg-subtle hover:text-navy"
              @click="resetModal.open = false"
            >
              <X :size="18" aria-hidden="true" />
            </button>
          </header>

          <div class="rounded-xl bg-background/80 px-3.5 py-2.5 text-xs">
            <p class="font-semibold text-navy">{{ resetModal.user?.hoTen || 'Chuyên gia' }}</p>
            <p class="mt-0.5 text-slate-500">@{{ resetModal.user?.tenTaiKhoan }} · {{ resetModal.user?.email }}</p>
          </div>

          <div v-if="resetModal.generatedPassword" class="space-y-3">
            <p class="text-xs text-slate-600">
              Mật khẩu mới đã được áp dụng và vô hiệu hóa phiên đăng nhập cũ. Hãy gửi mật khẩu này cho chuyên gia:
            </p>
            <div class="flex items-center justify-between gap-2 rounded-xl border border-teal/30 bg-teal/5 px-3.5 py-3">
              <code class="font-mono text-sm font-bold text-navy select-all">{{ resetModal.generatedPassword }}</code>
              <button
                type="button"
                class="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg bg-surface px-2.5 text-xs font-semibold text-teal-dark border border-border hover:border-teal"
                @click="copyGeneratedPassword"
              >
                <Check v-if="resetModal.copied" :size="13" aria-hidden="true" />
                <Copy v-else :size="13" aria-hidden="true" />
                <span>{{ resetModal.copied ? 'Đã chép' : 'Sao chép' }}</span>
              </button>
            </div>
            <footer class="flex justify-end border-t border-border/70 pt-3">
              <button type="button" class="ui-button ui-button--primary ui-button--sm" @click="resetModal.open = false">
                Hoàn tất
              </button>
            </footer>
          </div>

          <form v-else class="space-y-4" @submit.prevent="submitResetPassword">
            <div>
              <label for="expert-new-password" class="mb-1.5 block text-xs font-semibold text-navy">
                Mật khẩu mới (tùy chọn)
              </label>
              <input
                id="expert-new-password"
                v-model="resetModal.customPassword"
                type="text"
                minlength="8"
                maxlength="128"
                placeholder="Để trống để hệ thống tự sinh mật khẩu ngẫu nhiên"
                class="ui-input"
              >
              <p class="mt-1 text-[11px] text-slate-500">
                Tối thiểu 8 ký tự nếu tự nhập. Để trống để tự sinh mật khẩu tạm thời an toàn.
              </p>
            </div>

            <p v-if="resetModal.error" class="rounded-xl border border-danger/25 bg-danger/5 px-3 py-2 text-xs text-danger" role="alert">
              {{ resetModal.error }}
            </p>

            <footer class="flex justify-end gap-2 border-t border-border/70 pt-4">
              <button
                type="button"
                class="ui-button ui-button--outline ui-button--sm"
                :disabled="resetModal.submitting"
                @click="resetModal.open = false"
              >
                Hủy
              </button>
              <button
                type="submit"
                class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
                :disabled="resetModal.submitting"
              >
                <KeyRound :size="14" aria-hidden="true" />
                <span>{{ resetModal.submitting ? 'Đang cấp lại…' : 'Cấp lại mật khẩu' }}</span>
              </button>
            </footer>
          </form>
        </section>
      </div>
    </Transition>

    <!-- Create Expert Account Modal -->
    <Transition name="es-fade">
      <div
        v-if="createExpertModal.open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
        @click.self="createExpertModal.open = false"
      >
        <section class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-5" role="dialog" aria-modal="true">
          <header class="flex items-start justify-between border-b border-border/70 pb-3.5">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.08em] text-teal-dark">Quản lý chuyên gia</p>
              <h2 class="mt-0.5 font-display text-lg font-bold text-navy">Tạo tài khoản Chuyên gia mới</h2>
            </div>
            <button type="button" class="rounded-lg p-1.5 text-slate-400 hover:bg-subtle hover:text-navy" @click="createExpertModal.open = false">
              <X :size="18" aria-hidden="true" />
            </button>
          </header>

          <div v-if="createExpertModal.createdResult" class="space-y-4">
            <div class="rounded-xl border border-teal/25 bg-teal/5 p-4 text-xs leading-relaxed text-teal-dark">
              <p class="font-semibold">Tài khoản chuyên gia đã được tạo thành công!</p>
              <p class="mt-1">Chuyên gia sẽ bắt buộc đổi mật khẩu ở lần đăng nhập đầu tiên và hoàn thiện hồ sơ chuyên môn.</p>
            </div>
            <div class="rounded-xl border border-border bg-background p-4 space-y-2 text-xs">
              <p><span class="text-slate-500">Tài khoản:</span> <strong class="font-mono text-navy">{{ createExpertModal.createdResult.tenTaiKhoan }}</strong></p>
              <div class="flex items-center justify-between gap-2 pt-1">
                <p><span class="text-slate-500">Mật khẩu tạm thời:</span> <strong class="font-mono text-sm text-navy">{{ createExpertModal.createdResult.matKhauTamThoi }}</strong></p>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-navy hover:border-teal/50"
                  @click="copyCreatedExpertPassword"
                >
                  <Check v-if="createExpertModal.copied" :size="13" class="text-teal" aria-hidden="true" />
                  <Copy v-else :size="13" aria-hidden="true" />
                  <span>{{ createExpertModal.copied ? 'Đã sao chép' : 'Sao chép' }}</span>
                </button>
              </div>
            </div>
            <div class="flex justify-end">
              <UiButton size="sm" @click="createExpertModal.open = false">Đóng</UiButton>
            </div>
          </div>

          <form v-else class="space-y-3.5" @submit.prevent="submitCreateExpert">
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">Tên đăng nhập <span class="text-danger">*</span></label>
                <input v-model="createExpertModal.tenTaiKhoan" type="text" class="ui-input" placeholder="vd: expert.nguyena" required minlength="3" maxlength="50">
              </div>
              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">Họ và tên <span class="text-danger">*</span></label>
                <input v-model="createExpertModal.hoTen" type="text" class="ui-input" placeholder="Nguyễn Văn A" required>
              </div>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">Email <span class="text-danger">*</span></label>
                <input v-model="createExpertModal.email" type="email" class="ui-input" placeholder="expert@edusuggest.vn" required>
              </div>
              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">Số điện thoại</label>
                <input v-model="createExpertModal.soDienThoai" type="text" class="ui-input" placeholder="09xxxxxxxx">
              </div>
            </div>
            <div>
              <label class="mb-1 block text-xs font-semibold text-navy">Mật khẩu tạm thời (tùy chọn)</label>
              <input v-model="createExpertModal.matKhauTamThoi" type="text" class="ui-input" minlength="8" placeholder="Để trống để hệ thống tự sinh mật khẩu an toàn">
            </div>
            <p v-if="createExpertModal.error" class="rounded-xl border border-danger/25 bg-danger/5 px-3 py-2 text-xs text-danger">
              {{ createExpertModal.error }}
            </p>
            <footer class="flex justify-end gap-2 border-t border-border/70 pt-4">
              <button type="button" class="ui-button ui-button--outline ui-button--sm" @click="createExpertModal.open = false">Hủy</button>
              <UiButton type="submit" size="sm" :loading="createExpertModal.submitting">
                <UserPlus :size="14" aria-hidden="true" />
                <span>Tạo tài khoản</span>
              </UiButton>
            </footer>
          </form>
        </section>
      </div>
    </Transition>

    <!-- Verify Expert Profile Modal -->
    <Transition name="es-fade">
      <div
        v-if="verifyModal.open && verifyModal.expert"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
        @click.self="verifyModal.open = false"
      >
        <section class="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl space-y-5" role="dialog" aria-modal="true">
          <header class="flex items-start justify-between border-b border-border/70 pb-3.5">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.08em] text-teal-dark">Xác minh hồ sơ chuyên môn</p>
              <h2 class="mt-0.5 font-display text-lg font-bold text-navy">{{ verifyModal.expert.hoTen || verifyModal.expert.tenTaiKhoan }}</h2>
            </div>
            <button type="button" class="rounded-lg p-1.5 text-slate-400 hover:bg-subtle hover:text-navy" @click="verifyModal.open = false">
              <X :size="18" aria-hidden="true" />
            </button>
          </header>

          <div class="space-y-3 rounded-xl border border-border bg-background/70 p-4 text-xs">
            <div>
              <span class="font-semibold text-slate-500">Chuyên môn chính:</span>
              <span class="ml-1.5 font-semibold text-navy">{{ verifyModal.expert.primarySpecialty?.tenChuyenMon || 'Chưa chọn' }}</span>
            </div>
            <div v-if="verifyModal.expert.secondarySpecialties?.length">
              <span class="font-semibold text-slate-500">Chuyên môn phụ:</span>
              <span class="ml-1.5 text-navy">{{ verifyModal.expert.secondarySpecialties.map((s) => s.tenChuyenMon).join(', ') }}</span>
            </div>
            <div>
              <span class="font-semibold text-slate-500">Kinh nghiệm:</span>
              <span class="ml-1.5 text-navy">{{ verifyModal.expert.soNamKinhNghiem ?? 'Chưa cập nhật' }} năm</span>
            </div>
            <div v-if="verifyModal.expert.tieuSu">
              <span class="font-semibold text-slate-500">Mô tả:</span>
              <p class="mt-1 whitespace-pre-line text-slate-700">{{ verifyModal.expert.tieuSu }}</p>
            </div>
          </div>

          <form class="space-y-4" @submit.prevent="submitExpertVerification">
            <div class="grid grid-cols-2 gap-2.5">
              <label
                class="flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-xs font-semibold"
                :class="verifyModal.decision === 'VERIFIED' ? 'border-teal bg-teal/5 text-teal-dark' : 'border-border text-slate-600'"
              >
                <input v-model="verifyModal.decision" type="radio" value="VERIFIED" class="accent-teal">
                <span>Xác nhận hồ sơ</span>
              </label>
              <label
                class="flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-xs font-semibold"
                :class="verifyModal.decision === 'NEEDS_UPDATE' ? 'border-danger bg-danger/5 text-danger' : 'border-border text-slate-600'"
              >
                <input v-model="verifyModal.decision" type="radio" value="NEEDS_UPDATE" class="accent-danger">
                <span>Yêu cầu bổ sung</span>
              </label>
            </div>

            <div>
              <label class="mb-1 block text-xs font-semibold text-navy">
                Ghi chú xác minh <span v-if="verifyModal.decision === 'NEEDS_UPDATE'" class="text-danger">*</span>
              </label>
              <textarea
                v-model="verifyModal.note"
                rows="3"
                class="ui-input resize-y"
                :placeholder="verifyModal.decision === 'NEEDS_UPDATE' ? 'Nêu rõ thông tin chuyên gia cần bổ sung...' : 'Ghi chú nội bộ hoặc lời nhắn (tùy chọn)...'"
              />
            </div>

            <p v-if="verifyModal.error" class="rounded-xl border border-danger/25 bg-danger/5 px-3 py-2 text-xs text-danger">
              {{ verifyModal.error }}
            </p>

            <footer class="flex justify-end gap-2 border-t border-border/70 pt-4">
              <button type="button" class="ui-button ui-button--outline ui-button--sm" @click="verifyModal.open = false">Hủy</button>
              <UiButton type="submit" size="sm" :loading="verifyModal.submitting">
                <ShieldCheck :size="14" aria-hidden="true" />
                <span>Lưu quyết định</span>
              </UiButton>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </div>
</template>
