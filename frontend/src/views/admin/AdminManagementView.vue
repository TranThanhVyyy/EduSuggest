<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Save, Trash2, X } from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import api from '@/service/api'

const route = useRoute()
const resource = computed(() => route.meta.adminResource)
const titles = { users: 'Tài khoản', reviewers: 'Chuyên gia', providers: 'Nhà cung cấp', categories: 'Danh mục', courses: 'Khóa học', materials: 'Tài liệu' }
const title = computed(() => titles[resource.value] || 'Quản lý')
const rows = ref([])
const loading = ref(true)
const saving = ref(false)
const busyUserId = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const editorOpen = ref(false)
const editingId = ref(null)
const form = reactive({ tenDanhMuc: '', moTa: '' })
const canEditCategories = computed(() => resource.value === 'categories')
const columns = computed(() => resource.value === 'categories'
  ? [{ key: 'tenDanhMuc', label: 'Tên danh mục' }, { key: 'moTa', label: 'Mô tả' }]
  : resource.value === 'courses'
    ? [{ key: 'tieuDe', label: 'Tên khóa học' }, { key: 'trangThaiDuyet', label: 'Kiểm duyệt' }, { key: 'trangThaiHienThi', label: 'Hiển thị' }]
    : [{ key: 'hoTen', label: 'Họ tên' }, { key: 'email', label: 'Email' }, { key: 'tenVaiTro', label: 'Vai trò' }])

function unwrapResponseError(error, fallback) {
  return error.response?.data?.detail || fallback
}

async function loadRows() {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (resource.value === 'categories') {
      const { data } = await api.get('/admin/categories')
      rows.value = data
    } else if (resource.value === 'courses') {
      const { data } = await api.get('/admin/courses')
      rows.value = data
    } else if (['users', 'reviewers', 'providers'].includes(resource.value)) {
      const { data } = await api.get('/admin/users')
      const role = resource.value === 'reviewers' ? 'EXPERT' : resource.value === 'providers' ? 'PROVIDER' : null
      rows.value = role ? data.filter((user) => user.tenVaiTro === role) : data
    } else {
      rows.value = []
    }
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, `Không thể tải ${title.value.toLocaleLowerCase('vi')}.`)
  } finally { loading.value = false }
}

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
    successMessage.value = wasEditing ? 'Danh mục đã được cập nhật.' : 'Danh mục đã được tạo.'
  } catch (error) { errorMessage.value = unwrapResponseError(error, 'Không thể lưu danh mục.') }
  finally { saving.value = false }
}

async function deleteCategory(row) {
  if (!window.confirm(`Xóa danh mục “${row.tenDanhMuc}”?`)) return
  errorMessage.value = ''
  try {
    await api.delete(`/admin/categories/${row.maDanhMuc}`)
    await loadRows()
    successMessage.value = 'Danh mục đã được xóa.'
  } catch (error) { errorMessage.value = unwrapResponseError(error, 'Không thể xóa danh mục. Có thể danh mục vẫn đang được sử dụng.') }
}

async function grantExpertRole(user) {
  if (busyUserId.value !== null || user.tenVaiTro !== 'USER') return
  if (!window.confirm(`Cấp vai trò EXPERT cho ${user.hoTen || user.email || `tài khoản #${user.maNguoiDung}`}? Tài khoản sẽ được chuyển từ USER sang EXPERT.`)) return

  busyUserId.value = user.maNguoiDung
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const { data } = await api.post(`/admin/users/${user.maNguoiDung}/expert-role`, {})
    rows.value = rows.value.map((row) => row.maNguoiDung === data.maNguoiDung ? data : row)
    successMessage.value = `Đã cấp vai trò EXPERT cho ${data.hoTen || data.email || `tài khoản #${data.maNguoiDung}`}.`
  } catch (error) {
    errorMessage.value = unwrapResponseError(error, 'Không thể cấp vai trò EXPERT.')
  } finally {
    busyUserId.value = null
  }
}

watch(resource, loadRows)
onMounted(loadRows)
</script>

<template>
  <main class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5"><div><p class="ui-eyebrow">Quản trị</p><h1 class="ui-page-title mt-2">{{ title }}</h1><p class="mt-2 text-sm text-muted"></p></div><UiButton v-if="canEditCategories" @click="openCreate"><Plus :size="16" aria-hidden="true" /> Tạo danh mục</UiButton></header>
    <p v-if="errorMessage" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p><p v-if="successMessage" class="border-l-2 border-secondary py-2 pl-3 text-sm text-secondary" role="status">{{ successMessage }}</p>
    <p v-if="loading" class="py-5 text-sm text-muted" role="status">Đang tải dữ liệu…</p>
    <div v-else-if="['materials', 'providers'].includes(resource) && resource === 'materials'" class="border-l-2 border-accent py-1 pl-4" role="status"><h2 class="font-medium text-navy">Chưa có API quản trị tài liệu</h2><p class="mt-2 text-sm text-muted">Backend hiện chưa cung cấp danh sách tài liệu dành cho quản trị viên.</p></div>
    <div v-else-if="!rows.length" class="py-6 text-sm text-muted" role="status">{{ resource === 'providers' ? 'Danh sách nhà cung cấp chưa có API riêng; hồ sơ đăng ký được quản lý tại mục Hồ sơ đăng ký.' : 'Chưa có dữ liệu phù hợp.' }}</div>
    <div v-else class="overflow-x-auto border-y border-border"><table class="w-full min-w-[640px] text-left text-sm"><thead class="border-b border-border text-xs text-muted"><tr><th v-for="column in columns" :key="column.key" class="py-3 pr-4 font-medium">{{ column.label }}</th><th v-if="canEditCategories || resource === 'users'" class="py-3 text-right font-medium">Thao tác</th></tr></thead><tbody class="divide-y divide-border"><tr v-for="row in rows" :key="row.maDanhMuc || row.maNguoiDung || row.maKhoaHoc"><td v-for="column in columns" :key="column.key" class="py-4 pr-4 text-navy">{{ row[column.key] || '—' }}</td><td v-if="canEditCategories" class="py-3 text-right"><button class="px-2 py-1 text-secondary hover:underline" @click="openEdit(row)">Sửa</button><button class="px-2 py-1 text-danger hover:underline" @click="deleteCategory(row)" :aria-label="`Xóa ${row.tenDanhMuc}`"><Trash2 :size="15" /></button></td><td v-else-if="resource === 'users'" class="py-3 text-right"><UiButton v-if="row.tenVaiTro === 'USER'" size="sm" variant="outline" :loading="busyUserId === row.maNguoiDung" :disabled="busyUserId !== null" @click="grantExpertRole(row)">Cấp EXPERT</UiButton><span v-else class="text-xs text-muted">—</span></td></tr></tbody></table></div>

    <div v-if="editorOpen" class="fixed inset-0 z-50 flex items-end justify-center bg-navy/40 p-0 sm:items-center sm:p-4" @click.self="editorOpen = false"><section class="w-full max-w-lg space-y-5 bg-surface p-5 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="category-editor-title"><header class="flex items-start justify-between"><div><p class="ui-eyebrow">Danh mục</p><h2 id="category-editor-title" class="mt-1 text-xl font-medium text-navy">{{ editingId ? 'Sửa danh mục' : 'Tạo danh mục' }}</h2></div><button aria-label="Đóng" class="p-2 text-muted" @click="editorOpen = false"><X :size="18" /></button></header><form class="space-y-4" @submit.prevent="saveCategory"><label class="block text-sm font-medium text-navy">Tên danh mục<input v-model.trim="form.tenDanhMuc" class="ui-input mt-2" maxlength="255" required></label><label class="block text-sm font-medium text-navy">Mô tả<textarea v-model.trim="form.moTa" class="ui-input mt-2 min-h-24" rows="3"></textarea></label><p v-if="errorMessage" class="text-sm text-danger" role="alert">{{ errorMessage }}</p><div class="flex justify-end gap-2"><UiButton variant="quiet" @click="editorOpen = false">Hủy</UiButton><UiButton type="submit" :loading="saving"><Save :size="15" /> Lưu</UiButton></div></form></section></div>
  </main>
</template>
