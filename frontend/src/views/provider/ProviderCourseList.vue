<script setup>
import { computed, ref, watch } from 'vue'
import { BookOpen, Eye, FileEdit, Plus, Send, Trash2 } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  deleteProviderCourse,
  getProviderCourses,
  submitProviderCourseForReview,
} from '@/service/providerService'

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
const courses = computed(() => getProviderCourses())
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
  if ([PROVIDER_STATUS.pending, PROVIDER_STATUS.pendingAssignment, PROVIDER_STATUS.reviewing].includes(status)) return 'bg-primary/10 text-primary'
  if ([PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(status)) return 'bg-slate-100 text-navy'
  return 'bg-background text-muted'
}

function askAction(type, course) {
  pendingAction.value = { type, course }
  modalError.value = ''
  modalOpen.value = true
}

function performAction() {
  try {
    const { type, course } = pendingAction.value
    if (type === 'delete') {
      deleteProviderCourse(course.id)
      toastMessage.value = 'Đã xóa bản nháp trong phiên hiện tại.'
    } else {
      const wasResubmission = [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(course.status)
      submitProviderCourseForReview(course.id)
      toastMessage.value = wasResubmission
        ? 'Đã gửi lại khóa học để kiểm duyệt trong phiên hiện tại.'
        : 'Đã gửi khóa học để kiểm duyệt trong phiên hiện tại.'
    }
    modalOpen.value = false
    pendingAction.value = null
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể thực hiện thao tác.'
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
        <p class="text-sm text-muted">Quản lý khóa học</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Khóa học của tôi</h2>
        <p class="mt-2 text-sm leading-6 text-muted">Chỉ dữ liệu mock thuộc hồ sơ Provider minh họa đang được hiển thị.</p>
      </div>
      <RouterLink :to="{ name: 'provider-course-create' }" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
        <Plus :size="17" aria-hidden="true" /> Tạo khóa học
      </RouterLink>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(240px,1fr)_230px]">
        <SearchInput v-model="query" label="Tìm khóa học" placeholder="Tên khóa học, mã, danh mục..." />
        <label class="sr-only" for="provider-course-status">Lọc trạng thái kiểm duyệt</label>
        <select id="provider-course-status" v-model="statusFilter" class="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả trạng thái</option>
          <option v-for="(label, status) in PROVIDER_STATUS_LABELS" :key="status" :value="status">{{ label }}</option>
          <option value="feedback">Từ chối / yêu cầu chỉnh sửa</option>
        </select>
      </div>

      <div v-if="visibleCourses.length" class="overflow-x-auto">
        <table class="w-full min-w-[1050px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Khóa học</th>
              <th scope="col" class="px-4 py-3 font-semibold">Danh mục</th>
              <th scope="col" class="px-4 py-3 font-semibold">Cập nhật</th>
              <th scope="col" class="px-4 py-3 font-semibold">Chương / bài học</th>
              <th scope="col" class="px-4 py-3 font-semibold">Kiểm duyệt</th>
              <th scope="col" class="px-4 py-3 font-semibold">Hiển thị</th>
              <th scope="col" class="px-4 py-3 text-right font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="course in visibleCourses" :key="course.id" class="align-top hover:bg-background/70">
              <th scope="row" class="max-w-72 px-4 py-4">
                <div class="flex items-start gap-3">
                  <img v-if="course.coverImageUrl" :src="course.coverImageUrl" :alt="`Ảnh đại diện ${course.title}`" class="size-12 shrink-0 rounded-lg object-cover">
                  <span v-else class="flex size-12 shrink-0 items-center justify-center rounded-lg bg-background text-muted"><BookOpen :size="19" aria-hidden="true" /></span>
                  <span class="min-w-0">
                    <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="block line-clamp-2 font-semibold text-primary hover:underline">{{ course.title || 'Khóa học chưa đặt tên' }}</RouterLink>
                    <span class="mt-1 block text-xs font-normal text-muted">{{ course.id }}</span>
                  </span>
                </div>
              </th>
              <td class="px-4 py-4 text-muted">{{ course.category || '—' }}</td>
              <td class="whitespace-nowrap px-4 py-4 text-muted">{{ formatDate(course.updatedAt) }}</td>
              <td class="px-4 py-4 text-muted">{{ course.chapters.length }} chương · {{ course.chapters.reduce((sum, chapter) => sum + chapter.lessons.length, 0) }} bài</td>
              <td class="px-4 py-4"><span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" :class="statusClass(course.status)">{{ PROVIDER_STATUS_LABELS[course.status] || course.status }}</span></td>
              <td class="px-4 py-4 text-xs text-muted">{{ course.status === PROVIDER_STATUS.approved ? (course.visibility ? (course.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn') : 'Chưa có dữ liệu Backend') : 'Chưa công khai' }}</td>
              <td class="px-4 py-4 text-right">
                <div class="inline-flex flex-wrap justify-end gap-1">
                  <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Xem ${course.title}`" title="Xem chi tiết"><Eye :size="16" aria-hidden="true" /></RouterLink>
                  <RouterLink v-if="isEditable(course)" :to="{ name: 'provider-course-edit', params: { id: course.id } }" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-navy" :aria-label="`Chỉnh sửa ${course.title}`" title="Chỉnh sửa"><FileEdit :size="16" aria-hidden="true" /></RouterLink>
                  <button v-if="course.status === PROVIDER_STATUS.draft" type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Gửi ${course.title} kiểm duyệt`" title="Gửi kiểm duyệt" @click="askAction('submit', course)"><Send :size="15" aria-hidden="true" /></button>
                  <button v-if="course.status === PROVIDER_STATUS.draft" type="button" class="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-background hover:text-primary" :aria-label="`Xóa bản nháp ${course.title}`" title="Xóa bản nháp" @click="askAction('delete', course)"><Trash2 :size="15" aria-hidden="true" /></button>
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
      <p v-if="pendingAction?.type === 'delete'">Chỉ bản nháp chưa gửi kiểm duyệt mới có thể xóa. Thao tác chỉ ảnh hưởng đến dữ liệu mock trong phiên.</p>
      <p v-else>Khóa học chỉ được chuyển sang trạng thái chờ kiểm duyệt. Provider không thể tự phê duyệt hoặc công khai nội dung.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
