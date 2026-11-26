<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  CheckCircle2,
  Edit3,
  Layers,
  Plus,
  Power,
  RefreshCw,
  Save,
  Search,
  Users,
  X,
} from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import api from '@/service/api'

const SUGGESTED_GROUPS = [
  'Lập trình',
  'Frontend',
  'Backend',
  'Cơ sở dữ liệu',
  'AI và khoa học dữ liệu',
  'Mạng máy tính và bảo mật',
  'DevOps & Cloud',
  'Thiết kế UI/UX',
  'Phát triển ứng dụng di động',
  'Kiểm thử & QA',
]

const specialties = ref([])
const categories = ref([])
const loading = ref(true)
const saving = ref(false)
const busyId = ref(null)
const errorMessage = ref('')
const successMessage = ref('')

const searchQuery = ref('')
const selectedGroup = ref('')
const selectedStatus = ref('')

const modalOpen = ref(false)
const editingId = ref(null)
const form = reactive({
  tenChuyenMon: '',
  nhomChuyenMon: '',
  moTa: '',
  danhMucIds: [],
})

const availableGroups = computed(() => {
  const set = new Set(SUGGESTED_GROUPS)
  for (const item of specialties.value) {
    if (item.nhomChuyenMon) set.add(item.nhomChuyenMon)
  }
  return Array.from(set)
})

const filteredSpecialties = computed(() => {
  return specialties.value.filter((item) => {
    if (selectedGroup.value && item.nhomChuyenMon !== selectedGroup.value) return false
    if (selectedStatus.value && item.trangThai !== selectedStatus.value) return false
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase()
      const hay = `${item.tenChuyenMon} ${item.nhomChuyenMon} ${item.moTa || ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

const activeCount = computed(
  () => specialties.value.filter((item) => item.trangThai === 'ACTIVE').length,
)

function unwrapError(error, fallback) {
  return error.response?.data?.detail || fallback
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [specRes, catRes] = await Promise.all([
      api.get('/admin/specialties'),
      api.get('/admin/categories'),
    ])
    specialties.value = specRes.data || []
    categories.value = catRes.data || []
  } catch (error) {
    errorMessage.value = unwrapError(error, 'Không thể tải danh mục chuyên môn.')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    tenChuyenMon: '',
    nhomChuyenMon: '',
    moTa: '',
    danhMucIds: [],
  })
  modalOpen.value = true
}

function openEdit(item) {
  editingId.value = item.maChuyenMon
  Object.assign(form, {
    tenChuyenMon: item.tenChuyenMon || '',
    nhomChuyenMon: item.nhomChuyenMon || '',
    moTa: item.moTa || '',
    danhMucIds: (item.danhMucs || []).map((c) => c.maDanhMuc),
  })
  modalOpen.value = true
}

function toggleCategory(catId) {
  if (form.danhMucIds.includes(catId)) {
    form.danhMucIds = form.danhMucIds.filter((id) => id !== catId)
  } else {
    form.danhMucIds = [...form.danhMucIds, catId]
  }
}

async function saveSpecialty() {
  if (saving.value) return
  if (!form.tenChuyenMon.trim() || !form.nhomChuyenMon.trim()) {
    errorMessage.value = 'Vui lòng nhập đầy đủ Tên chuyên môn và Nhóm chuyên môn.'
    return
  }
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = {
      tenChuyenMon: form.tenChuyenMon.trim(),
      nhomChuyenMon: form.nhomChuyenMon.trim(),
      moTa: form.moTa.trim() || null,
      danhMucIds: form.danhMucIds,
    }
    const wasEditing = editingId.value !== null
    if (wasEditing) {
      await api.patch(`/admin/specialties/${editingId.value}`, payload)
    } else {
      await api.post('/admin/specialties', payload)
    }
    modalOpen.value = false
    await loadData()
    successMessage.value = wasEditing
      ? 'Đã cập nhật thông tin chuyên môn.'
      : 'Đã thêm chuyên môn mới vào danh mục hệ thống.'
  } catch (error) {
    errorMessage.value = unwrapError(error, 'Không thể lưu chuyên môn.')
  } finally {
    saving.value = false
  }
}

async function toggleStatus(item) {
  if (busyId.value === item.maChuyenMon) return
  const nextStatus = item.trangThai === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  busyId.value = item.maChuyenMon
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const { data } = await api.patch(`/admin/specialties/${item.maChuyenMon}/status`, {
      trangThai: nextStatus,
    })
    specialties.value = specialties.value.map((s) =>
      s.maChuyenMon === data.maChuyenMon ? data : s,
    )
    successMessage.value =
      nextStatus === 'ACTIVE'
        ? `Đã kích hoạt lại chuyên môn "${data.tenChuyenMon}".`
        : `Đã ngừng sử dụng chuyên môn "${data.tenChuyenMon}" (dữ liệu chuyên gia cũ vẫn được bảo toàn).`
  } catch (error) {
    errorMessage.value = unwrapError(error, 'Không thể thay đổi trạng thái chuyên môn.')
  } finally {
    busyId.value = null
  }
}

function handleEscape(event) {
  if (event.key === 'Escape' && modalOpen.value) {
    modalOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
  loadData()
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
          Nội dung &amp; Kiểm duyệt
        </p>
        <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">
          Danh mục chuyên môn chuyên gia
        </h1>
        <p class="mt-1.5 text-sm text-slate-600">
          Chuẩn hóa danh mục chuyên môn độc lập và ánh xạ với các danh mục khóa học/tài liệu để phục vụ phân công kiểm duyệt.
        </p>
      </div>

      <div class="flex shrink-0 flex-wrap items-center gap-2.5">
        <UiButton variant="primary" size="sm" @click="openCreate">
          <Plus :size="15" aria-hidden="true" />
          <span>Thêm chuyên môn</span>
        </UiButton>
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </header>

    <!-- Summary Strip -->
    <div v-if="!loading" class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-2xl border border-border bg-surface px-4 py-3.5">
        <p class="text-xs font-medium text-slate-500">Tổng chuyên môn</p>
        <p class="mt-1 text-2xl font-bold tabular-nums text-navy">{{ specialties.length }}</p>
      </div>
      <div class="rounded-2xl border border-border bg-surface px-4 py-3.5">
        <p class="text-xs font-medium text-slate-500">Đang hoạt động</p>
        <p class="mt-1 text-2xl font-bold tabular-nums text-teal-dark">{{ activeCount }}</p>
      </div>
      <div class="rounded-2xl border border-border bg-surface px-4 py-3.5">
        <p class="text-xs font-medium text-slate-500">Số nhóm chuyên môn</p>
        <p class="mt-1 text-2xl font-bold tabular-nums text-navy">
          {{ new Set(specialties.map((s) => s.nhomChuyenMon)).size }}
        </p>
      </div>
    </div>

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

    <!-- Filter Bar -->
    <div
      v-if="!loading"
      class="flex flex-col justify-between gap-3 rounded-2xl border border-border bg-surface px-4 py-3.5 sm:flex-row sm:items-center"
    >
      <div class="flex flex-1 flex-wrap items-center gap-3">
        <div class="relative min-w-[220px] max-w-sm flex-1">
          <Search :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Tìm theo tên, nhóm hoặc mô tả..."
            class="ui-input h-9 pl-9 text-xs"
          >
        </div>

        <select v-model="selectedGroup" class="ui-input h-9 w-52 text-xs">
          <option value="">Tất cả nhóm chuyên môn</option>
          <option v-for="group in availableGroups" :key="group" :value="group">
            {{ group }}
          </option>
        </select>

        <select v-model="selectedStatus" class="ui-input h-9 w-44 text-xs">
          <option value="">Tất cả trạng thái</option>
          <option value="ACTIVE">Đang sử dụng</option>
          <option value="INACTIVE">Ngừng sử dụng</option>
        </select>
      </div>

      <div class="flex items-center gap-2 text-xs text-slate-500">
        <span class="tabular-nums">{{ filteredSpecialties.length }} / {{ specialties.length }} chuyên môn</span>
        <button
          v-if="searchQuery || selectedGroup || selectedStatus"
          type="button"
          class="inline-flex items-center gap-1 font-semibold text-teal hover:underline"
          @click="searchQuery = ''; selectedGroup = ''; selectedStatus = ''"
        >
          <X :size="12" aria-hidden="true" />
          <span>Xóa lọc</span>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="rounded-2xl border border-border bg-surface p-5">
      <UiSkeleton variant="table" :lines="6" />
    </div>

    <!-- Empty -->
    <div v-else-if="!filteredSpecialties.length" class="rounded-2xl border border-border bg-surface p-6">
      <UiEmptyState
        title="Không tìm thấy chuyên môn phù hợp"
        description="Thêm chuyên môn mới hoặc điều chỉnh bộ lọc hiện tại."
        action-label="Thêm chuyên môn"
        @action="openCreate"
      />
    </div>

    <!-- Table -->
    <div v-else class="overflow-hidden rounded-2xl border border-border bg-surface shadow-xs">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px] text-left text-sm">
          <thead class="border-b border-border/80 bg-background text-[11px] font-semibold uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th class="px-5 py-3">Chuyên môn &amp; Mô tả</th>
              <th class="px-5 py-3">Nhóm</th>
              <th class="px-5 py-3">Danh mục liên kết</th>
              <th class="px-5 py-3 text-center">Chuyên gia</th>
              <th class="px-5 py-3">Trạng thái</th>
              <th class="px-5 py-3 text-center">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr
              v-for="item in filteredSpecialties"
              :key="item.maChuyenMon"
              class="align-middle transition-colors hover:bg-background/70"
            >
              <td class="px-5 py-3.5">
                <div class="font-semibold text-navy">{{ item.tenChuyenMon }}</div>
                <p v-if="item.moTa" class="mt-0.5 max-w-md text-xs leading-relaxed text-slate-500">
                  {{ item.moTa }}
                </p>
              </td>
              <td class="whitespace-nowrap px-5 py-3.5">
                <span class="inline-flex items-center gap-1 rounded-lg bg-subtle px-2.5 py-1 text-xs font-medium text-navy">
                  <Layers :size="12" class="text-slate-400" aria-hidden="true" />
                  <span>{{ item.nhomChuyenMon }}</span>
                </span>
              </td>
              <td class="px-5 py-3.5">
                <div v-if="item.danhMucs?.length" class="flex max-w-xs flex-wrap gap-1.5">
                  <span
                    v-for="cat in item.danhMucs"
                    :key="cat.maDanhMuc"
                    class="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-slate-600"
                  >
                    {{ cat.tenDanhMuc }}
                  </span>
                </div>
                <span v-else class="text-xs text-slate-400">Chưa gắn danh mục</span>
              </td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center gap-1 text-xs font-semibold tabular-nums text-navy">
                  <Users :size="13" class="text-slate-400" aria-hidden="true" />
                  <span>{{ item.soChuyenGiaDangSuDung }}</span>
                </span>
              </td>
              <td class="whitespace-nowrap px-5 py-3.5">
                <span
                  class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold"
                  :class="item.trangThai === 'ACTIVE'
                    ? 'border-teal/25 bg-teal/10 text-teal-dark'
                    : 'border-slate-200 bg-slate-100 text-slate-500'"
                >
                  <span
                    class="size-1.5 rounded-full"
                    :class="item.trangThai === 'ACTIVE' ? 'bg-teal' : 'bg-slate-400'"
                    aria-hidden="true"
                  />
                  <span>{{ item.trangThai === 'ACTIVE' ? 'Đang sử dụng' : 'Ngừng sử dụng' }}</span>
                </span>
              </td>
              <td class="whitespace-nowrap px-5 py-3.5 text-center">
                <div class="inline-flex items-center gap-2">
                  <button
                    type="button"
                    class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy transition-colors hover:border-teal/50 hover:text-teal"
                    @click="openEdit(item)"
                  >
                    <Edit3 :size="13" aria-hidden="true" />
                    <span>Sửa</span>
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-semibold transition-colors disabled:opacity-50"
                    :class="item.trangThai === 'ACTIVE'
                      ? 'border-amber/30 bg-amber/5 text-amber hover:bg-amber/10'
                      : 'border-teal/30 bg-teal/5 text-teal-dark hover:bg-teal/10'"
                    :disabled="busyId === item.maChuyenMon"
                    @click="toggleStatus(item)"
                  >
                    <Power :size="13" aria-hidden="true" />
                    <span>{{ item.trangThai === 'ACTIVE' ? 'Ẩn' : 'Bật lại' }}</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create / Edit Specialty Modal -->
    <div
      v-if="modalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-navy/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      @click.self="modalOpen = false"
    >
      <div class="w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-surface shadow-xl">
        <div class="flex items-center justify-between border-b border-border/80 px-5 py-4">
          <h2 class="font-display text-base font-bold text-navy">
            {{ editingId ? 'Chỉnh sửa chuyên môn' : 'Thêm chuyên môn mới' }}
          </h2>
          <button
            type="button"
            class="flex size-8 items-center justify-center rounded-lg text-slate-400 hover:bg-subtle hover:text-navy"
            aria-label="Đóng"
            @click="modalOpen = false"
          >
            <X :size="16" aria-hidden="true" />
          </button>
        </div>

        <form class="max-h-[75vh] space-y-4 overflow-y-auto p-5" @submit.prevent="saveSpecialty">
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 block text-xs font-semibold text-navy">
                Tên chuyên môn <span class="text-danger">*</span>
              </label>
              <input
                v-model="form.tenChuyenMon"
                type="text"
                class="ui-input"
                placeholder="VD: React, Python, SQL..."
                required
              >
            </div>
            <div>
              <label class="mb-1.5 block text-xs font-semibold text-navy">
                Nhóm chuyên môn <span class="text-danger">*</span>
              </label>
              <input
                v-model="form.nhomChuyenMon"
                type="text"
                list="specialty-group-suggestions"
                class="ui-input"
                placeholder="Chọn hoặc nhập nhóm mới"
                required
              >
              <datalist id="specialty-group-suggestions">
                <option v-for="g in availableGroups" :key="g" :value="g" />
              </datalist>
            </div>
          </div>

          <div>
            <label class="mb-1.5 block text-xs font-semibold text-navy">Mô tả chuyên môn</label>
            <textarea
              v-model="form.moTa"
              rows="3"
              class="ui-input resize-y"
              placeholder="Mô tả ngắn gọn phạm vi kiến thức để chuyên gia dễ chọn và hỗ trợ phân công..."
            />
          </div>

          <div>
            <label class="mb-2 block text-xs font-semibold text-navy">
              Ánh xạ danh mục khóa học / tài liệu (chọn nhiều)
            </label>
            <div class="grid gap-2 sm:grid-cols-2">
              <label
                v-for="cat in categories"
                :key="cat.maDanhMuc"
                class="flex cursor-pointer items-center gap-2.5 rounded-xl border px-3 py-2 text-xs transition-colors"
                :class="form.danhMucIds.includes(cat.maDanhMuc)
                  ? 'border-teal bg-teal/[0.06] font-semibold text-navy'
                  : 'border-border bg-background/60 text-slate-600 hover:border-slate-300'"
              >
                <input
                  type="checkbox"
                  :checked="form.danhMucIds.includes(cat.maDanhMuc)"
                  class="size-3.5 rounded accent-teal"
                  @change="toggleCategory(cat.maDanhMuc)"
                >
                <span class="truncate">{{ cat.tenDanhMuc }}</span>
              </label>
            </div>
          </div>

          <div class="flex justify-end gap-2.5 border-t border-border/80 pt-4">
            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm"
              @click="modalOpen = false"
            >
              Hủy
            </button>
            <UiButton type="submit" size="sm" :loading="saving">
              <Save :size="14" aria-hidden="true" />
              <span>{{ editingId ? 'Lưu thay đổi' : 'Tạo chuyên môn' }}</span>
            </UiButton>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
