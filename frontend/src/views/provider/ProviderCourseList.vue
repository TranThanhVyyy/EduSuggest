<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BookOpen, Eye, FileEdit, MoreHorizontal, Plus, Send, Trash2 } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  deleteProviderCourseRecord,
  loadProviderCategories,
  loadProviderCourses,
  providerErrorMessage,
  submitProviderCourseRecord,
} from '@/service/providerApiService'

const pageSize = 8
const route = useRoute()
const router = useRouter()
const query = ref('')
const statusFilter = ref(typeof route.query.status === 'string' ? route.query.status : '')
const currentPage = ref(1)
const modalOpen = ref(false)
const modalError = ref('')
const pendingAction = ref(null)
const toastMessage = ref('')
const courses = ref([])
const categoryNames = ref(new Map())
const isLoading = ref(true)
const loadError = ref('')
const isSubmitting = ref(false)
const openMenuCourseId = ref('')

function closeActionMenu() {
  openMenuCourseId.value = ''
}

function toggleActionMenu(courseId) {
  openMenuCourseId.value = openMenuCourseId.value === courseId ? '' : courseId
}

function handleDocumentClick(event) {
  if (!openMenuCourseId.value) return
  if (!event.target.closest?.('[data-course-action-menu]')) {
    closeActionMenu()
  }
}

function handleDocumentKeydown(event) {
  if (event.key === 'Escape' && openMenuCourseId.value) {
    closeActionMenu()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
})

async function refreshCourses() {
  isLoading.value = true
  loadError.value = ''
  const [coursesRes, categoriesRes] = await Promise.allSettled([
    loadProviderCourses(),
    loadProviderCategories(),
  ])
  if (categoriesRes.status === 'fulfilled') {
    categoryNames.value = new Map(categoriesRes.value.map((c) => [String(c.id), c.name]))
  }
  if (coursesRes.status === 'fulfilled') {
    courses.value = coursesRes.value.map((course) => ({
      ...course,
      category: categoryNames.value.get(String(course.categoryId)) || course.category,
    }))
  } else {
    loadError.value = providerErrorMessage(coursesRes.reason, 'Không thể tải danh sách khóa học.')
  }
  isLoading.value = false
}

refreshCourses()
const filteredCourses = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return courses.value.filter((course) => {
    const text = `${course.id} ${course.title} ${course.category}`.toLocaleLowerCase('vi')
    const matchesText = !search || text.includes(search)
    const matchesStatus = !statusFilter.value
      || (statusFilter.value === 'feedback'
        ? [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(course.status)
        : course.status === statusFilter.value)
    return matchesText && matchesStatus
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))
const visibleCourses = computed(() =>
  filteredCourses.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch(() => route.query.status, (value) => {
  statusFilter.value = typeof value === 'string' ? value : ''
  currentPage.value = 1
})
watch(statusFilter, (value) => {
  const nextQuery = { ...route.query }
  if (value) nextQuery.status = value
  else delete nextQuery.status
  router.replace({ query: nextQuery })
})
watch([query, statusFilter], () => { currentPage.value = 1 })
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function isEditable(course) {
  return [PROVIDER_STATUS.draft, PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(course.status)
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}

function statusClass(status) {
  if (status === PROVIDER_STATUS.approved) return 'bg-accent/10 text-accent'
  if (status === PROVIDER_STATUS.pending) return 'bg-primary/10 text-primary'
  if ([PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(status)) return 'bg-slate-100 text-navy'
  return 'bg-background text-muted'
}

function askAction(type, course) {
  closeActionMenu()
  pendingAction.value = { type, course }
  modalError.value = ''
  modalOpen.value = true
}

async function performAction() {
  if (isSubmitting.value) return
  isSubmitting.value = true
  try {
    const { type, course } = pendingAction.value
    if (type === 'delete') {
      await deleteProviderCourseRecord(course.id)
      await refreshCourses()
      toastMessage.value = 'Đã xóa bản nháp khóa học.'
    } else {
      const wasResubmission = [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(course.status)
      await submitProviderCourseRecord(course.id)
      await refreshCourses()
      loadError.value = ''
      toastMessage.value = wasResubmission
        ? 'Đã gửi lại khóa học để chuyên gia thẩm định.'
        : 'Đã gửi khóa học vào hàng đợi kiểm duyệt.'
    }
    modalOpen.value = false
    pendingAction.value = null
  } catch (error) {
    modalError.value = providerErrorMessage(error, 'Không thể thực hiện thao tác.')
  } finally {
    isSubmitting.value = false
  }
}

const modalTitle = computed(() => {
  if (pendingAction.value?.type === 'delete') return 'Xác nhận xóa bản nháp'
  return 'Xác nhận gửi kiểm duyệt'
})

const modalDescription = computed(() => {
  const course = pendingAction.value?.course
  if (!course) return ''
  return `${course.title || 'Khóa học chưa đặt tên'} · ${PROVIDER_STATUS_LABELS[course.status]}`
})
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Quản lý khóa học</p>
        <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">Khóa học của tôi</h1>
        <p class="mt-1.5 text-sm text-slate-600">Quản lý bản nháp, chỉnh sửa bài giảng và theo dõi trạng thái kiểm duyệt khóa học.</p>
      </div>
      <RouterLink :to="{ name: 'provider-course-create' }" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
        <Plus :size="17" aria-hidden="true" /> Tạo khóa học
      </RouterLink>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 px-5 py-4 md:grid-cols-[minmax(240px,1fr)_220px]">
        <SearchInput v-model="query" label="Tìm khóa học" placeholder="Tên khóa học, mã, danh mục..." />
        <label class="sr-only" for="provider-course-status">Lọc trạng thái kiểm duyệt</label>
        <select id="provider-course-status" v-model="statusFilter" class="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả trạng thái</option>
          <option v-for="(label, status) in PROVIDER_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
          <option value="feedback">Từ chối / yêu cầu chỉnh sửa</option>
        </select>
      </div>

      <p v-if="isLoading" class="p-5 text-sm text-muted" role="status">Đang tải khóa học…</p>
      <p v-else-if="loadError" class="m-4 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-primary" role="alert">{{ loadError }} <button type="button" class="ml-2 font-semibold underline" @click="refreshCourses">Thử lại</button></p>
      <div v-else-if="visibleCourses.length" class="overflow-x-auto lg:overflow-visible">
        <table class="w-full min-w-[920px] text-left text-sm">
          <colgroup>
            <col class="w-[32%]">
            <col class="w-[19%]">
            <col class="w-[9%]">
            <col class="w-[11%]">
            <col class="w-[12%]">
            <col class="w-[17%]">
          </colgroup>
          <thead class="bg-background text-[11px] uppercase tracking-[0.06em] text-slate-500">
            <tr>
              <th scope="col" class="whitespace-nowrap px-5 py-3 font-semibold">Khóa học</th>
              <th scope="col" class="whitespace-nowrap px-3.5 py-3 font-semibold">Danh mục</th>
              <th scope="col" class="whitespace-nowrap px-3.5 py-3 font-semibold">Bài học</th>
              <th scope="col" class="whitespace-nowrap px-3.5 py-3 font-semibold">Cập nhật</th>
              <th scope="col" class="whitespace-nowrap px-3.5 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="whitespace-nowrap px-5 py-3 text-center font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="course in visibleCourses" :key="course.id" class="align-middle transition-colors duration-150 hover:bg-background/70">
              <th scope="row" class="px-5 py-4 font-normal">
                <div class="flex items-center gap-3">
                  <img
                    v-if="course.coverImageUrl"
                    :src="course.coverImageUrl"
                    :alt="`Ảnh đại diện ${course.title}`"
                    class="h-11 w-[72px] shrink-0 rounded-lg border border-border object-cover"
                  >
                  <span
                    v-else
                    class="flex h-11 w-[72px] shrink-0 items-center justify-center rounded-lg border border-border bg-subtle text-slate-500"
                  >
                    <BookOpen :size="16" aria-hidden="true" />
                  </span>
                  <div class="min-w-0 flex-1">
                    <RouterLink
                      :to="{ name: 'provider-course-detail', params: { id: course.id } }"
                      class="block break-words [overflow-wrap:anywhere] text-sm font-semibold leading-snug text-navy hover:text-teal hover:underline"
                    >
                      {{ course.title || 'Khóa học chưa đặt tên' }}
                    </RouterLink>
                    <span class="mt-0.5 block text-xs text-slate-500 tabular-nums">#{{ course.id }}</span>
                  </div>
                </div>
              </th>
              <td class="px-3.5 py-4 text-xs leading-relaxed text-slate-600">
                {{ course.category || 'Chưa phân loại' }}
              </td>
              <td class="whitespace-nowrap px-3.5 py-4 text-xs font-medium text-slate-600 tabular-nums">
                {{ course.lessons.length }} bài học
              </td>
              <td class="whitespace-nowrap px-3.5 py-4 text-xs text-slate-500 tabular-nums">
                {{ formatDate(course.updatedAt) }}
              </td>
              <td class="whitespace-nowrap px-3.5 py-4">
                <div class="flex flex-col items-start gap-1">
                  <span
                    class="inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold"
                    :class="statusClass(course.status)"
                  >
                    {{ PROVIDER_STATUS_LABELS[course.status] || course.status }}
                  </span>
                  <span class="inline-flex items-center gap-1.5 pl-1 text-[11px] text-slate-500">
                    <span
                      class="size-1.5 rounded-full"
                      :class="course.visibility === 'VISIBLE' ? 'bg-teal' : 'bg-slate-300'"
                      aria-hidden="true"
                    ></span>
                    <span>{{ course.visibility === 'VISIBLE' ? 'Đang hiển thị' : 'Đang ẩn' }}</span>
                  </span>
                </div>
              </td>
              <td class="whitespace-nowrap px-5 py-4 text-center align-middle">
                <div class="inline-flex flex-nowrap items-center justify-center gap-2">
                  <RouterLink
                    v-if="isEditable(course)"
                    :to="{ name: 'provider-course-edit', params: { id: course.id } }"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy shadow-[0_1px_2px_rgba(17,34,51,0.04)] transition-colors duration-150 hover:border-navy/25 hover:bg-subtle/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                  >
                    <FileEdit :size="13" class="shrink-0 text-slate-500" aria-hidden="true" />
                    <span>Chỉnh sửa</span>
                  </RouterLink>

                  <RouterLink
                    v-else
                    :to="{ name: 'provider-course-detail', params: { id: course.id } }"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy shadow-[0_1px_2px_rgba(17,34,51,0.04)] transition-colors duration-150 hover:border-navy/25 hover:bg-subtle/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                  >
                    <Eye :size="13" class="shrink-0 text-slate-500" aria-hidden="true" />
                    <span>Xem chi tiết</span>
                  </RouterLink>

                  <button
                    v-if="course.status === PROVIDER_STATUS.draft"
                    type="button"
                    class="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg bg-teal px-3 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(13,148,136,0.22)] transition-colors duration-150 hover:bg-teal-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                    @click="askAction('submit', course)"
                  >
                    <Send :size="13" class="shrink-0" aria-hidden="true" />
                    <span>Gửi duyệt</span>
                  </button>

                  <div
                    v-if="isEditable(course)"
                    class="relative"
                    data-course-action-menu
                  >
                    <button
                      type="button"
                      class="flex size-8 items-center justify-center rounded-lg border border-transparent text-slate-400 transition-colors duration-150 hover:border-border hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
                      :aria-label="`Thao tác khác cho ${course.title}`"
                      :aria-expanded="openMenuCourseId === course.id"
                      @click="toggleActionMenu(course.id)"
                    >
                      <MoreHorizontal :size="16" aria-hidden="true" />
                    </button>

                    <Transition name="es-popover">
                      <div
                        v-if="openMenuCourseId === course.id"
                        class="absolute right-0 top-9 z-30 w-44 origin-top-right rounded-xl border border-border bg-surface p-1.5 text-left shadow-lg"
                      >
                        <RouterLink
                          :to="{ name: 'provider-course-detail', params: { id: course.id } }"
                          class="flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-navy transition-colors duration-150 hover:bg-subtle"
                          @click="closeActionMenu"
                        >
                          <Eye :size="14" class="text-slate-400" aria-hidden="true" />
                          <span>Xem chi tiết</span>
                        </RouterLink>

                        <div v-if="course.status === PROVIDER_STATUS.draft" class="my-1 border-t border-border/70"></div>

                        <button
                          v-if="course.status === PROVIDER_STATUS.draft"
                          type="button"
                          class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-danger transition-colors duration-150 hover:bg-danger/10"
                          @click="askAction('delete', course)"
                        >
                          <Trash2 :size="14" aria-hidden="true" />
                          <span>Xóa bản nháp</span>
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
      <EmptyState v-else title="Không có khóa học phù hợp" description="Thử đổi từ khóa tìm kiếm hoặc bộ lọc trạng thái." />
      <PaginationControls v-if="filteredCourses.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredCourses.length" />
    </section>

    <AdminModal
      :open="modalOpen"
      mode="confirm"
      :title="modalTitle"
      :description="modalDescription"
      :confirm-label="pendingAction?.type === 'delete' ? 'Xóa bản nháp' : 'Gửi kiểm duyệt'"
      :error="modalError"
      @close="modalOpen = false"
      @confirm="performAction"
    >
      <p v-if="pendingAction?.type === 'delete'">Chỉ bản nháp đang ẩn, chưa gửi duyệt và chưa có bài học, đăng ký, lịch sử học hoặc nhận xét mới được xóa. Backend sẽ từ chối nếu khóa học có dữ liệu liên quan.</p>
      <p v-else>Khóa học chỉ được chuyển sang trạng thái chờ kiểm duyệt. Provider không thể tự phê duyệt hoặc công khai nội dung.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
