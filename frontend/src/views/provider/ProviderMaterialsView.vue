<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen,
  Edit3,
  ExternalLink,
  FileText,
  Filter,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  X,
} from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  createStandaloneMaterial,
  deleteStandaloneMaterial,
  loadProviderCategories,
  loadProviderCourses,
  loadProviderMaterials,
  providerErrorMessage,
  submitStandaloneMaterial,
  updateStandaloneMaterial,
  uploadStandaloneMaterialFile,
} from '@/service/providerApiService'
import { isProtectedMaterialUrl, openMaterialFile } from '@/service/materialFileService'

const materials = ref([])
const categories = ref([])
const courses = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const toastMessage = ref('')
const selectedFile = ref(null)
const currentFileUrl = ref('')
const openingFileId = ref('')

const modalOpen = ref(false)
const editingId = ref(null)
const openMenuId = ref('')
const confirmModal = reactive({
  open: false,
  type: '',
  material: null,
  submitting: false,
})
const form = reactive({
  title: '',
  documentType: 'DOCUMENT',
  fileUrl: '',
  description: '',
  categoryId: '',
  courseId: '',
})

const searchQuery = ref('')
const selectedStatus = ref('')

async function refreshData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [matList, catList, courseList] = await Promise.all([
      loadProviderMaterials(),
      loadProviderCategories().catch(() => []),
      loadProviderCourses().catch(() => []),
    ])
    materials.value = matList
    categories.value = catList
    courses.value = courseList
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể tải danh sách tài liệu.')
  } finally {
    loading.value = false
  }
}

const route = useRoute()
const router = useRouter()

const categoryNameMap = computed(
  () => new Map(categories.value.map((cat) => [String(cat.id), cat.name])),
)

function getCategoryName(categoryId) {
  if (!categoryId) return ''
  return categoryNameMap.value.get(String(categoryId)) || `Danh mục #${categoryId}`
}

function isEditableMaterial(mat) {
  return ['Draft', 'DRAFT', 'TuChoi', 'YeuCauChinhSua'].includes(mat.reviewStatus)
}

function closeActionMenu() {
  openMenuId.value = ''
}

function toggleActionMenu(id) {
  openMenuId.value = openMenuId.value === id ? '' : id
}

function handleDocumentClick(event) {
  if (!openMenuId.value) return
  if (!event.target.closest?.('[data-material-action-menu]')) {
    closeActionMenu()
  }
}

function handleEscape(event) {
  if (event.key === 'Escape') {
    if (modalOpen.value) modalOpen.value = false
    if (confirmModal.open) confirmModal.open = false
    if (openMenuId.value) closeActionMenu()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentClick)
  document.addEventListener('keydown', handleEscape)
  refreshData()
  if (route.query.create === '1') {
    openCreateModal()
    router.replace({ name: 'provider-materials-manage' })
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentClick)
  document.removeEventListener('keydown', handleEscape)
})

watch(
  () => route.query.create,
  (val) => {
    if (val === '1') {
      openCreateModal()
      router.replace({ name: 'provider-materials-manage' })
    }
  },
)

const filteredMaterials = computed(() => {
  return materials.value.filter((mat) => {
    if (selectedStatus.value && mat.reviewStatus !== selectedStatus.value) return false
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase()
      const inTitle = mat.title?.toLowerCase().includes(q)
      const inDesc = mat.description?.toLowerCase().includes(q)
      if (!inTitle && !inDesc) return false
    }
    return true
  })
})

function openCreateModal() {
  editingId.value = null
  Object.assign(form, {
    title: '',
    documentType: 'DOCUMENT',
    fileUrl: '',
    description: '',
    categoryId: '',
    courseId: '',
  })
  selectedFile.value = null
  currentFileUrl.value = ''
  errorMessage.value = ''
  modalOpen.value = true
}

function openEditModal(mat) {
  editingId.value = mat.id
  Object.assign(form, {
    title: mat.title,
    documentType: mat.documentType || 'DOCUMENT',
    fileUrl: isProtectedMaterialUrl(mat.fileUrl) ? '' : mat.fileUrl,
    description: mat.description,
    categoryId: mat.categoryId ? String(mat.categoryId) : '',
    courseId: mat.courseId ? String(mat.courseId) : '',
  })
  selectedFile.value = null
  currentFileUrl.value = mat.fileUrl || ''
  errorMessage.value = ''
  modalOpen.value = true
}

async function saveMaterial() {
  if (!form.title.trim() || (!form.fileUrl.trim() && !selectedFile.value && !currentFileUrl.value)) {
    errorMessage.value = 'Tiêu đề và URL hoặc tệp tải lên là bắt buộc.'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    let saved
    if (editingId.value) {
      const values = {
        title: form.title,
        documentType: form.documentType,
        description: form.description,
        categoryId: form.categoryId || null,
        courseId: form.courseId || null,
      }
      if (form.fileUrl.trim()) values.fileUrl = form.fileUrl.trim()
      saved = await updateStandaloneMaterial(editingId.value, values)
      toastMessage.value = 'Đã cập nhật tài liệu.'
    } else {
      saved = await createStandaloneMaterial({
        title: form.title,
        documentType: form.documentType,
        fileUrl: form.fileUrl.trim(),
        description: form.description,
        categoryId: form.categoryId || null,
        courseId: form.courseId || null,
      })
      toastMessage.value = 'Đã tạo tài liệu thành công ở trạng thái Bản nháp.'
    }
    if (selectedFile.value) {
      await uploadStandaloneMaterialFile(saved.id, selectedFile.value)
      toastMessage.value = 'Đã lưu thông tin và tải tệp riêng tư lên thành công.'
    }
    modalOpen.value = false
    await refreshData()
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu tài liệu.')
  } finally {
    saving.value = false
  }
}

function selectPrivateFile(event) {
  selectedFile.value = event.target.files?.[0] || null
  if (selectedFile.value) form.fileUrl = ''
}

async function openMaterial(mat, download = false) {
  openingFileId.value = mat.id
  errorMessage.value = ''
  try {
    await openMaterialFile({ id: mat.id, fileUrl: mat.fileUrl, title: mat.title }, { download })
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể truy cập tệp tài liệu.')
  } finally {
    openingFileId.value = ''
  }
}

function askConfirm(type, mat) {
  closeActionMenu()
  if (type === 'submit' && !mat.courseId && !mat.lessonId && !mat.categoryId) {
    errorMessage.value = 'Vui lòng chọn danh mục cho tài liệu trước khi gửi kiểm duyệt.'
    return
  }
  confirmModal.type = type
  confirmModal.material = mat
  confirmModal.open = true
}

async function runConfirmedAction() {
  const mat = confirmModal.material
  if (!mat || confirmModal.submitting) return
  confirmModal.submitting = true
  errorMessage.value = ''
  try {
    if (confirmModal.type === 'delete') {
      await deleteStandaloneMaterial(mat.id)
      toastMessage.value = 'Đã xóa tài liệu.'
    } else {
      await submitStandaloneMaterial(mat.id)
      toastMessage.value = 'Đã gửi tài liệu tới Chuyên gia kiểm duyệt.'
    }
    confirmModal.open = false
    confirmModal.material = null
    await refreshData()
  } catch (error) {
    errorMessage.value = providerErrorMessage(
      error,
      confirmModal.type === 'delete' ? 'Không thể xóa tài liệu.' : 'Không thể gửi duyệt tài liệu.',
    )
    confirmModal.open = false
  } finally {
    confirmModal.submitting = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <ToastMessage :message="toastMessage" @dismiss="toastMessage = ''" />

    <!-- Header -->
    <header class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="ui-eyebrow">Quản lý nội dung học liệu</p>
        <h1 class="ui-page-title mt-1.5">Tài liệu học tập của tôi</h1>
        <p class="mt-1 text-sm text-muted">
          Quản lý tài liệu độc lập và học liệu liên kết khóa học, gửi kiểm duyệt chuyên gia.
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <UiButton
          variant="primary"
          @click="openCreateModal"
        >
          <Plus :size="16" aria-hidden="true" />
          <span>Tạo tài liệu mới</span>
        </UiButton>

        <button
          type="button"
          class="ui-button ui-button--secondary inline-flex items-center gap-2 text-xs"
          :disabled="loading"
          @click="refreshData"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </header>

    <!-- Error Alert -->
    <UiAlert
      v-if="errorMessage"
      variant="danger"
      :message="errorMessage"
      dismissible
      @dismiss="errorMessage = ''"
    />

    <!-- Filter Bar -->
    <div v-if="!loading && materials.length" class="bento-card p-3.5 bg-surface flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex flex-1 items-center gap-3">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Tìm theo tiêu đề tài liệu..."
          class="ui-input text-xs max-w-sm"
        >
        <select
          v-model="selectedStatus"
          class="ui-input text-xs w-44"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="Draft">Bản nháp</option>
          <option value="ChoKiemDuyet">Chờ duyệt</option>
          <option value="DaPheDuyet">Đã phê duyệt</option>
          <option value="TuChoi">Bị từ chối</option>
          <option value="YeuCauChinhSua">Cần chỉnh sửa</option>
        </select>
      </div>

      <div class="text-xs text-muted">
        Hiển thị {{ filteredMaterials.length }} / {{ materials.length }} tài liệu
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="bento-card p-4">
      <UiSkeleton variant="table" :lines="6" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!materials.length" class="bento-card bg-surface p-8">
      <UiEmptyState
        title="Chưa có tài liệu học tập nào"
        description="Bạn có thể tạo tài liệu độc lập hoặc tài liệu liên kết khóa học để cung cấp cho người học trên EduSuggest."
        action-label="Tạo tài liệu đầu tiên"
        @action="openCreateModal"
      />
    </div>

    <!-- Table -->
    <div v-else class="bento-card p-0 bg-surface shadow-sm">
      <div class="overflow-x-auto lg:overflow-visible">
        <table class="w-full min-w-[780px] text-left text-sm">
          <thead class="border-b border-border bg-subtle/80 text-[11px] font-bold uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th class="whitespace-nowrap px-5 py-3">Tài liệu</th>
              <th class="whitespace-nowrap px-4 py-3">Định dạng</th>
              <th class="whitespace-nowrap px-4 py-3">Danh mục</th>
              <th class="whitespace-nowrap px-4 py-3">Kiểm duyệt</th>
              <th class="whitespace-nowrap px-4 py-3">Hiển thị</th>
              <th class="whitespace-nowrap px-5 py-3 text-center">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr
              v-for="mat in filteredMaterials"
              :key="mat.id"
              class="align-middle transition-colors duration-150 hover:bg-subtle/40"
            >
              <td class="px-5 py-4">
                <div class="break-words [overflow-wrap:anywhere] text-sm font-semibold text-navy">{{ mat.title }}</div>
                <div class="mt-0.5 text-xs text-slate-500 truncate max-w-xs">{{ mat.description || 'Không có mô tả' }}</div>
              </td>
              <td class="whitespace-nowrap px-4 py-4">
                <span class="rounded border border-border bg-subtle px-2 py-0.5 text-xs font-bold uppercase text-ink">
                  {{ mat.documentType }}
                </span>
              </td>
              <td class="px-4 py-4 text-xs text-slate-600">
                <span v-if="mat.categoryId" class="font-medium text-navy">{{ getCategoryName(mat.categoryId) }}</span>
                <span v-else class="text-slate-500">Chưa phân danh mục</span>
                <span v-if="mat.courseId" class="mt-0.5 block text-[11px] text-teal-dark">Thuộc khóa học #{{ mat.courseId }}</span>
              </td>
              <td class="whitespace-nowrap px-4 py-4">
                <UiStatusBadge :status="mat.reviewStatus" />
                <p v-if="mat.rejectionReason" class="mt-1 text-[11px] text-danger max-w-xs truncate" :title="mat.rejectionReason">
                  Ghi chú: {{ mat.rejectionReason }}
                </p>
              </td>
              <td class="whitespace-nowrap px-4 py-4">
                <UiStatusBadge :status="mat.visibility" />
              </td>
              <td class="whitespace-nowrap px-5 py-4 text-center align-middle">
                <div class="inline-flex flex-nowrap items-center justify-center gap-2">
                  <button
                    v-if="isEditableMaterial(mat)"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy shadow-[0_1px_2px_rgba(17,34,51,0.04)] transition-colors duration-150 hover:border-navy/25 hover:bg-subtle/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                    @click="openEditModal(mat)"
                  >
                    <Edit3 :size="13" class="shrink-0 text-slate-500" aria-hidden="true" />
                    <span>Chỉnh sửa</span>
                  </button>

                  <button
                    v-if="isEditableMaterial(mat)"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal px-3 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(13,148,136,0.22)] transition-colors duration-150 hover:bg-teal-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                    @click="askConfirm('submit', mat)"
                  >
                    <Send :size="13" class="shrink-0" aria-hidden="true" />
                    <span>Gửi duyệt</span>
                  </button>

                  <button
                    v-if="!isEditableMaterial(mat) && mat.fileUrl"
                    type="button"
                    :disabled="openingFileId === mat.id"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy shadow-[0_1px_2px_rgba(17,34,51,0.04)] transition-colors duration-150 hover:border-navy/25 hover:bg-subtle/70"
                    @click="openMaterial(mat)"
                  >
                    <ExternalLink :size="13" class="shrink-0 text-slate-500" aria-hidden="true" />
                    <span>{{ openingFileId === mat.id ? 'Đang mở…' : 'Mở tệp' }}</span>
                  </button>

                  <div
                    v-if="isEditableMaterial(mat)"
                    class="relative"
                    data-material-action-menu
                  >
                    <button
                      type="button"
                      class="flex size-8 items-center justify-center rounded-lg border border-transparent text-slate-400 transition-colors duration-150 hover:border-border hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                      :aria-label="`Thao tác khác cho ${mat.title}`"
                      :aria-expanded="openMenuId === mat.id"
                      @click="toggleActionMenu(mat.id)"
                    >
                      <MoreHorizontal :size="16" aria-hidden="true" />
                    </button>

                    <Transition name="es-popover">
                      <div
                        v-if="openMenuId === mat.id"
                        class="absolute right-0 top-9 z-30 w-44 origin-top-right rounded-xl border border-border bg-surface p-1.5 text-left shadow-lg"
                      >
                        <button
                          v-if="mat.fileUrl"
                          type="button"
                          class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-navy transition-colors duration-150 hover:bg-subtle"
                          @click="closeActionMenu(); openMaterial(mat)"
                        >
                          <ExternalLink :size="14" class="text-slate-400" aria-hidden="true" />
                          <span>Mở liên kết tệp</span>
                        </button>

                        <div v-if="mat.fileUrl" class="my-1 border-t border-border/70"></div>

                        <button
                          type="button"
                          class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-danger transition-colors duration-150 hover:bg-danger/10"
                          @click="askConfirm('delete', mat)"
                        >
                          <Trash2 :size="14" aria-hidden="true" />
                          <span>Xóa tài liệu</span>
                        </button>
                      </div>
                    </Transition>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirmation Modal (Submit / Delete) -->
    <Transition name="es-fade">
      <div
        v-if="confirmModal.open"
        class="fixed inset-0 z-[60] flex items-end justify-center bg-navy/45 p-0 backdrop-blur-[2px] sm:items-center sm:p-4"
        @click.self="confirmModal.open = false"
      >
        <section
          class="w-full max-w-md rounded-t-2xl border border-border bg-surface p-5 shadow-2xl sm:rounded-2xl sm:p-6"
          role="dialog"
          aria-modal="true"
        >
          <h2 class="font-display text-lg font-bold text-navy">
            {{ confirmModal.type === 'delete' ? 'Xác nhận xóa tài liệu' : 'Xác nhận gửi kiểm duyệt' }}
          </h2>
          <p class="mt-2 text-sm text-slate-600">
            <template v-if="confirmModal.type === 'delete'">
              Bạn có chắc chắn muốn xóa tài liệu <strong class="text-navy">{{ confirmModal.material?.title }}</strong>? Hành động này không thể hoàn tác.
            </template>
            <template v-else>
              Tài liệu <strong class="text-navy">{{ confirmModal.material?.title }}</strong> sẽ được chuyển sang trạng thái <strong>Chờ kiểm duyệt</strong> để Chuyên gia thẩm định.
            </template>
          </p>
          <footer class="mt-6 flex flex-col-reverse gap-2 border-t border-border/70 pt-4 sm:flex-row sm:justify-end">
            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm"
              :disabled="confirmModal.submitting"
              @click="confirmModal.open = false"
            >
              Hủy
            </button>
            <button
              type="button"
              class="ui-button ui-button--sm"
              :class="confirmModal.type === 'delete' ? 'bg-danger text-white hover:opacity-90' : 'ui-button--primary'"
              :disabled="confirmModal.submitting"
              @click="runConfirmedAction"
            >
              {{ confirmModal.submitting ? 'Đang xử lý…' : (confirmModal.type === 'delete' ? 'Xóa tài liệu' : 'Gửi kiểm duyệt') }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>

    <!-- Modal Form (Create / Edit) -->
    <Transition name="es-fade">
      <div
        v-if="modalOpen"
        class="fixed inset-0 z-[60] flex items-end justify-center bg-navy/45 p-0 backdrop-blur-[2px] sm:items-center sm:p-4"
        @click.self="modalOpen = false"
      >
        <section
          class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-border bg-surface p-5 shadow-2xl sm:rounded-2xl sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="provider-material-modal-title"
        >
          <header class="flex items-start justify-between gap-4 border-b border-border/70 pb-4">
            <div>
              <h2 id="provider-material-modal-title" class="font-display text-lg font-bold text-navy">
                {{ editingId ? 'Chỉnh sửa tài liệu học tập' : 'Tạo tài liệu học tập mới' }}
              </h2>
              <p class="mt-1 text-xs text-slate-600 sm:text-sm">
                {{ editingId ? 'Cập nhật thông tin tài liệu học tập.' : 'Điền thông tin tài liệu học tập độc lập để lưu bản nháp hoặc gửi kiểm duyệt.' }}
              </p>
            </div>
            <button
              type="button"
              class="flex size-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors duration-150 hover:bg-subtle hover:text-navy"
              aria-label="Đóng hộp thoại"
              @click="modalOpen = false"
            >
              <X :size="18" aria-hidden="true" />
            </button>
          </header>

          <form class="mt-5 space-y-4 text-xs sm:text-sm" @submit.prevent="saveMaterial">
            <div>
              <label for="material-title" class="mb-1.5 block font-semibold text-navy">
                Tiêu đề tài liệu <span class="text-danger">*</span>
              </label>
              <input
                id="material-title"
                v-model="form.title"
                type="text"
                required
                placeholder="Ví dụ: Cẩm nang thực hành Machine Learning nâng cao"
                class="ui-input"
              >
            </div>

            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label for="material-type" class="mb-1.5 block font-semibold text-navy">Định dạng tài liệu</label>
                <select id="material-type" v-model="form.documentType" class="ui-input">
                  <option value="DOCUMENT">DOCUMENT</option>
                  <option value="PDF">PDF</option>
                  <option value="SLIDE">SLIDE</option>
                  <option value="CODE">CODE</option>
                  <option value="EXERCISE">EXERCISE</option>
                  <option value="REFERENCE">REFERENCE</option>
                </select>
              </div>

              <div>
                <label for="material-category" class="mb-1.5 block font-semibold text-navy">Danh mục kiến thức</label>
                <select id="material-category" v-model="form.categoryId" class="ui-input">
                  <option value="">Không phân danh mục</option>
                  <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <label for="material-url" class="mb-1.5 block font-semibold text-navy">
                URL tài liệu ngoài
              </label>
              <input
                id="material-url"
                v-model="form.fileUrl"
                type="url"
                :disabled="Boolean(selectedFile)"
                placeholder="https://example.org/material.pdf"
                class="ui-input"
              >
              <p class="mt-1 text-[11px] text-muted">URL ngoài không thể được EduSuggest thu hồi sau khi đã chia sẻ.</p>
            </div>

            <div class="rounded-xl border border-border bg-subtle/40 p-3.5">
              <label for="material-private-file" class="mb-1.5 block font-semibold text-navy">
                Hoặc tải tệp riêng tư lên EduSuggest
              </label>
              <input
                id="material-private-file"
                type="file"
                accept=".pdf,.txt,.csv,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.webp"
                class="block w-full text-xs text-ink file:mr-3 file:rounded-lg file:border-0 file:bg-teal file:px-3 file:py-2 file:font-semibold file:text-white hover:file:bg-teal-dark"
                @change="selectPrivateFile"
              >
              <p class="mt-2 text-[11px] text-muted">Tối đa 25 MB. Tệp được lưu ngoài thư mục public và cần xác thực khi mở.</p>
              <p v-if="currentFileUrl && isProtectedMaterialUrl(currentFileUrl) && !selectedFile" class="mt-1 text-[11px] font-medium text-teal">
                Tài liệu đang có tệp riêng tư. Chọn tệp mới để thay thế.
              </p>
            </div>

            <div>
              <label for="material-description" class="mb-1.5 block font-semibold text-navy">Mô tả tài liệu</label>
              <textarea
                id="material-description"
                v-model="form.description"
                rows="3"
                placeholder="Mô tả tóm tắt nội dung và cách tiếp cận học liệu..."
                class="ui-input"
              />
            </div>

            <p
              v-if="errorMessage"
              class="rounded-xl border border-danger/25 bg-danger/5 px-3.5 py-2.5 text-xs font-medium text-danger"
              role="alert"
            >
              {{ errorMessage }}
            </p>

            <footer class="flex flex-col-reverse gap-2 border-t border-border/70 pt-4 sm:flex-row sm:justify-end">
              <button
                type="button"
                class="ui-button ui-button--outline ui-button--sm"
                :disabled="saving"
                @click="modalOpen = false"
              >
                Hủy
              </button>
              <button
                type="submit"
                class="ui-button ui-button--primary ui-button--sm"
                :disabled="saving"
              >
                {{ saving ? 'Đang lưu…' : (editingId ? 'Lưu thay đổi' : 'Tạo tài liệu') }}
              </button>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </div>
</template>
