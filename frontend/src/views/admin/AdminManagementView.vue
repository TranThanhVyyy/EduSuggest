<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronDown, Eye, LockKeyhole, Pencil, Plus, Trash2, UnlockKeyhole } from 'lucide-vue-next'
import AdminModal from '@/components/admin/AdminModal.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { ADMIN_RESOURCE_CONFIGS } from '@/constant/adminResources'
import {
  deleteAdminCategory,
  getAdminCourseLessons,
  getAdminRows,
  saveAdminRecord,
  toggleAdminAccount,
} from '@/service/adminService'

const pageSize = 8
const route = useRoute()
const router = useRouter()
const query = ref('')
const filters = reactive({})
const currentPage = ref(1)
const modalOpen = ref(false)
const modalMode = ref('view')
const modalRecord = ref(null)
const modalError = ref('')
const toastMessage = ref('')
const pendingAction = ref(null)
const expandedCourseId = ref('')

const config = computed(() => ADMIN_RESOURCE_CONFIGS[route.meta.adminResource] || null)
const records = computed(() => (config.value ? getAdminRows(config.value.key) : []))
const filteredRecords = computed(() => {
  if (!config.value) return []
  const search = query.value.trim().toLocaleLowerCase('vi')

  return records.value.filter((record) => {
    const matchesText = !search || config.value.searchFields.some((key) =>
      String(record[key] ?? '').toLocaleLowerCase('vi').includes(search),
    ) || (config.value.key === 'courses' && getAdminCourseLessons(record.id).some((lesson) =>
      `${lesson.id} ${lesson.title} ${lesson.chapter}`.toLocaleLowerCase('vi').includes(search),
    ))
    const matchesFilters = config.value.filters.every((filter) => {
      const selected = filters[filter.key]
      return !selected || String(record[filter.key] ?? '') === String(selected)
    })
    return matchesText && matchesFilters
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRecords.value.length / pageSize)))
const visibleRecords = computed(() =>
  filteredRecords.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch(
  () => route.meta.adminResource,
  () => {
    query.value = ''
    currentPage.value = 1
    expandedCourseId.value = ''
    for (const key of Object.keys(filters)) delete filters[key]
  },
)
watch([query, filters], () => { currentPage.value = 1 })
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function formatCell(record, key) {
  const value = record[key]
  if (key === 'permissions') return Array.isArray(value) ? `${value.length} quyền` : value || 'Chưa có dữ liệu'
  if (key === 'status') {
    return value === 'active' ? 'Đang hoạt động' : value === 'locked' ? 'Đã khóa' : value === 'inactive' ? 'Ngừng hoạt động' : value || 'Chưa có dữ liệu'
  }
  if (key === 'visibility') return value === 'visible' ? 'Đang hiển thị' : value === 'hidden' ? 'Đã ẩn' : 'Chưa có dữ liệu'
  if (key === 'reviewStatus') return value === 'DaPheDuyet' ? 'Đã phê duyệt' : 'Chưa có dữ liệu'
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return value.toLocaleString('vi-VN')
  if (key.toLowerCase().endsWith('at') || key.endsWith('Date')) {
    const date = new Date(value)
    if (!Number.isNaN(date.getTime())) return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
  }
  if (Array.isArray(value)) return value.join(', ')
  return value
}

function openView(record) {
  modalRecord.value = record
  modalMode.value = 'view'
  modalError.value = ''
  modalOpen.value = true
}

function openCreate() {
  modalRecord.value = null
  modalMode.value = 'form'
  modalError.value = ''
  modalOpen.value = true
}

function openEdit(record) {
  if (record.isProtected) {
    toastMessage.value = 'Vai trò Admin được bảo vệ và không thể chỉnh sửa.'
    return
  }
  modalRecord.value = record
  modalMode.value = 'form'
  modalError.value = ''
  modalOpen.value = true
}

function openDetailRoute(record) {
  router.push({ name: config.value.detailRoute, params: { id: record.id } })
}

function toggleCourseLessons(courseId) {
  expandedCourseId.value = expandedCourseId.value === courseId ? '' : courseId
}

function lessonsForCourse(courseId) {
  return getAdminCourseLessons(courseId)
}

function confirmToggle(record) {
  pendingAction.value = {
    type: 'toggle',
    record,
    title: record.status === 'active' ? 'Xác nhận khóa tài khoản' : 'Xác nhận mở khóa tài khoản',
    description: record.status === 'active'
      ? `Tài khoản "${record.fullName || record.name}" sẽ bị khóa.`
      : `Tài khoản "${record.fullName || record.name}" sẽ được mở khóa.`,
  }
  modalMode.value = 'confirm'
  modalRecord.value = record
  modalError.value = ''
  modalOpen.value = true
}

function confirmDelete(record) {
  pendingAction.value = {
    type: 'delete',
    record,
    title: 'Xác nhận xóa danh mục',
    description: `Bạn có chắc muốn xóa danh mục "${record.name}"?`,
  }
  modalMode.value = 'confirm'
  modalRecord.value = record
  modalError.value = ''
  modalOpen.value = true
}

function saveRecord(values) {
  try {
    saveAdminRecord(config.value.key, values)
    modalOpen.value = false
    toastMessage.value = values.id ? 'Đã cập nhật dữ liệu mẫu trong phiên.' : 'Đã thêm dữ liệu mẫu trong phiên.'
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể lưu dữ liệu.'
  }
}

function performConfirmedAction() {
  try {
    if (pendingAction.value?.type === 'toggle') {
      toggleAdminAccount(config.value.key, pendingAction.value.record.id)
      toastMessage.value = 'Đã cập nhật trạng thái tài khoản trong phiên.'
    } else if (pendingAction.value?.type === 'delete') {
      deleteAdminCategory(pendingAction.value.record.id)
      toastMessage.value = 'Đã xóa danh mục trong phiên.'
    }
    modalOpen.value = false
    pendingAction.value = null
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể thực hiện thao tác.'
  }
}

function closeModal() {
  modalOpen.value = false
  pendingAction.value = null
}
</script>

<template>
  <div v-if="config" class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">{{ config.section }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ config.title }}</h2>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">{{ config.description }}</p>
      </div>
      <button v-if="config.canCreate" type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90" @click="openCreate">
        <Plus :size="17" aria-hidden="true" /> Thêm mới
      </button>
    </section>

    <p v-if="config.readOnlyContent" class="rounded-xl border border-primary/15 bg-primary/5 p-3 text-sm text-navy">
      Đây là danh sách nội dung đã được Reviewer phê duyệt. Admin không tạo, đăng tải hoặc thay đổi nội dung khóa học, bài học hay tài liệu.
    </p>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(240px,1fr)_repeat(auto-fit,minmax(170px,220px))]">
        <SearchInput v-model="query" :label="`Tìm ${config.title.toLocaleLowerCase('vi')}`" :placeholder="`Tìm theo ${config.searchFields.slice(0, 3).join(', ')}...`" />
        <label v-for="filter in config.filters" :key="filter.key" class="sr-only" :for="`admin-filter-${filter.key}`">{{ filter.label }}</label>
        <select
          v-for="filter in config.filters"
          :id="`admin-filter-${filter.key}`"
          :key="filter.key"
          v-model="filters[filter.key]"
          class="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
        >
          <option value="">{{ filter.label }}</option>
          <option v-for="option in filter.options" :key="option.value ?? option" :value="option.value ?? option">{{ option.label ?? option }}</option>
        </select>
      </div>

      <div v-if="visibleRecords.length" class="overflow-x-auto">
        <table class="w-full min-w-[880px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th v-for="column in config.columns" :key="column.key" scope="col" class="whitespace-nowrap px-4 py-3 font-semibold">{{ column.label }}</th>
              <th scope="col" class="px-4 py-3 text-right font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="record in visibleRecords" :key="record.id">
              <tr class="align-top hover:bg-background/70">
                <td v-for="(column, columnIndex) in config.columns" :key="column.key" class="max-w-72 px-4 py-3.5 text-muted">
                  <span v-if="column.key === 'status'" class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" :class="record.status === 'active' ? 'bg-accent/10 text-accent' : record.status === 'locked' ? 'bg-primary/10 text-primary' : 'bg-background text-muted'">{{ formatCell(record, column.key) }}</span>
                  <span v-else-if="column.key === 'visibility'" class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" :class="record.visibility === 'visible' ? 'bg-accent/10 text-accent' : 'bg-background text-muted'">{{ formatCell(record, column.key) }}</span>
                  <RouterLink v-else-if="config.detailRoute && columnIndex === 1" :to="{ name: config.detailRoute, params: { id: record.id } }" class="line-clamp-2 font-semibold text-primary hover:underline">{{ formatCell(record, column.key) }}</RouterLink>
                  <span v-else class="line-clamp-2" :class="columnIndex === 0 ? 'font-medium text-navy' : ''">{{ formatCell(record, column.key) }}</span>
                </td>
                <td class="whitespace-nowrap px-4 py-3.5 text-right">
                  <div class="inline-flex items-center justify-end gap-1">
                    <button
                      v-if="config.key === 'courses'"
                      type="button"
                      class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary"
                      :aria-label="`${expandedCourseId === record.id ? 'Thu gọn' : 'Mở'} bài học của ${record.title}`"
                      :aria-expanded="expandedCourseId === record.id"
                      title="Xem bài học trong khóa học"
                      @click="toggleCourseLessons(record.id)"
                    >
                      <ChevronDown :size="16" :class="expandedCourseId === record.id ? 'rotate-180' : ''" aria-hidden="true" />
                    </button>
                    <button type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Xem ${record.fullName || record.name || record.title || record.id}`" title="Xem chi tiết" @click="config.detailRoute ? openDetailRoute(record) : openView(record)">
                      <Eye :size="16" aria-hidden="true" />
                    </button>
                    <button v-if="config.canEdit && !record.isProtected" type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-navy" :aria-label="`Chỉnh sửa ${record.fullName || record.name || record.id}`" title="Chỉnh sửa" @click="openEdit(record)">
                      <Pencil :size="15" aria-hidden="true" />
                    </button>
                    <button v-if="config.canToggle && !record.isProtected" type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-primary" :aria-label="record.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa tài khoản'" :title="record.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa tài khoản'" @click="confirmToggle(record)">
                      <LockKeyhole v-if="record.status === 'active'" :size="15" aria-hidden="true" />
                      <UnlockKeyhole v-else :size="15" aria-hidden="true" />
                    </button>
                    <button v-if="config.canDelete" type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Xóa danh mục ${record.name}`" title="Xóa" @click="confirmDelete(record)">
                      <Trash2 :size="15" aria-hidden="true" />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="config.key === 'courses' && expandedCourseId === record.id" class="bg-background/70">
                <td :colspan="config.columns.length + 1" class="px-4 py-4">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <p class="text-sm font-semibold text-navy">Bài học trong khóa học · {{ lessonsForCourse(record.id).length }} bài học có dữ liệu mẫu</p>
                    <RouterLink :to="{ name: 'admin-course-detail', params: { id: record.id } }" class="text-xs font-semibold text-primary hover:underline">Mở chi tiết khóa học</RouterLink>
                  </div>
                  <div v-if="lessonsForCourse(record.id).length" class="mt-3 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white px-3">
                    <div v-for="lesson in lessonsForCourse(record.id)" :key="lesson.id" class="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div class="min-w-0">
                        <p class="text-sm font-semibold text-navy">{{ lesson.order }}. {{ lesson.title }}</p>
                        <p class="mt-1 text-xs text-muted">{{ lesson.chapter }} · {{ lesson.duration }} · {{ lesson.contentType }}</p>
                      </div>
                      <RouterLink :to="{ name: 'admin-lesson-detail', params: { id: lesson.id } }" class="shrink-0 text-xs font-semibold text-primary hover:underline">Xem bài học</RouterLink>
                    </div>
                  </div>
                  <p v-else class="mt-3 rounded-xl border border-dashed border-slate-200 bg-white p-4 text-sm text-muted">Chưa có bài học được duyệt trong dữ liệu mẫu.</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="Không có dữ liệu phù hợp" description="Thử đổi từ khóa tìm kiếm hoặc bộ lọc." />
      <PaginationControls v-if="filteredRecords.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredRecords.length" />
    </section>

    <AdminModal
      :open="modalOpen"
      :mode="modalMode"
      :title="pendingAction?.title || (modalMode === 'view' ? 'Thông tin chi tiết' : modalRecord ? 'Chỉnh sửa thông tin' : 'Thêm mới')"
      :description="pendingAction?.description || ''"
      :record="modalRecord"
      :fields="modalMode === 'view' ? config.detailFields : config.fields"
      :confirm-label="pendingAction?.type === 'delete' ? 'Xóa danh mục' : pendingAction?.type === 'toggle' && modalRecord?.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa tài khoản'"
      :error="modalError"
      @close="closeModal"
      @save="saveRecord"
      @confirm="performConfirmedAction"
    >
      <p v-if="pendingAction?.type === 'delete'">Thao tác này chỉ thực hiện trên dữ liệu mẫu trong phiên hiện tại.</p>
      <p v-else>Trạng thái kiểm duyệt không thay đổi khi khóa hoặc mở khóa tài khoản.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
  <EmptyState v-else title="Không tìm thấy trang quản lý" description="Đường dẫn Admin không có cấu hình tương ứng." />
</template>
