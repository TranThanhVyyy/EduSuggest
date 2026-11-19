<script setup>
import { computed, ref, watch } from 'vue'
import { UserRoundCheck } from 'lucide-vue-next'
import AdminModal from '@/components/admin/AdminModal.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  assignAdminReviewer,
  autoAssignAdminReviewers,
  getAdminReviewRequests,
  getAdminReviewerWorkload,
  getAdminRows,
} from '@/service/adminService'

const pageSize = 8
const query = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const modalOpen = ref(false)
const selectedRequest = ref(null)
const modalRecord = ref(null)
const modalError = ref('')
const toastMessage = ref('')
const autoAssignConfirmOpen = ref(false)
const autoAssignSummary = ref(null)

const reviewers = computed(() => getAdminRows('reviewers'))
const activeReviewers = computed(() => reviewers.value.filter((reviewer) => reviewer.status === 'active'))
const assignmentFields = computed(() => [{
  key: 'reviewerId',
  label: 'Chuyên gia phụ trách',
  type: 'select',
  placeholder: 'Chọn Reviewer đang hoạt động',
  required: true,
  options: activeReviewers.value.map((reviewer) => ({
    value: reviewer.id,
    label: `${reviewer.fullName} · ${reviewer.expertise} · ${getAdminReviewerWorkload(reviewer.id)} việc`,
  })),
}])
const requests = computed(() => getAdminReviewRequests())
const unassignedRequests = computed(() => requests.value.filter((request) => !request.assignedReviewerId))
const filteredRequests = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return requests.value.filter((request) => {
    const text = `${request.id} ${request.title} ${request.creator} ${request.reviewerName}`.toLocaleLowerCase('vi')
    return (!search || text.includes(search))
      && (!typeFilter.value || request.itemType === typeFilter.value)
      && (!statusFilter.value || request.status === statusFilter.value)
  })
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRequests.value.length / pageSize)))
const visibleRequests = computed(() => filteredRequests.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))

watch([query, typeFilter, statusFilter], () => { currentPage.value = 1 })
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function statusLabel(status) {
  return status === 'DangKiemDuyet' ? 'Đang kiểm duyệt' : status === 'YeuCauChinhSua' ? 'Yêu cầu chỉnh sửa' : 'Chờ kiểm duyệt'
}

function formatDate(value) {
  if (!value) return 'Chưa phân công'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa phân công' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}

function openAssignment(request) {
  selectedRequest.value = request
  modalRecord.value = { id: request.id, reviewerId: request.assignedReviewerId || '' }
  modalError.value = ''
  modalOpen.value = true
}

function saveAssignment(values) {
  try {
    assignAdminReviewer(selectedRequest.value.id, values.reviewerId)
    const reviewer = activeReviewers.value.find((item) => item.id === values.reviewerId)
    toastMessage.value = `Đã phân công "${selectedRequest.value.title}" cho ${reviewer?.fullName || 'Reviewer'} trong phiên.`
    modalOpen.value = false
    selectedRequest.value = null
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể phân công Reviewer.'
  }
}

function runAutomaticAssignment() {
  try {
    autoAssignSummary.value = autoAssignAdminReviewers()
    const assignedCount = autoAssignSummary.value.assigned.length
    const unmatchedCount = autoAssignSummary.value.unassigned.length
    toastMessage.value = `Đã tự động phân công ${assignedCount} yêu cầu${unmatchedCount ? `; ${unmatchedCount} yêu cầu chưa khớp chuyên môn` : ''}.`
    autoAssignConfirmOpen.value = false
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể tự động phân công Reviewer.'
  }
}
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Kiểm duyệt</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Phân công Reviewer</h2>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">Tự động phân công theo danh mục và chuyên môn của Reviewer đang hoạt động; các yêu cầu chưa có chuyên gia phù hợp sẽ được giữ lại để Admin xử lý.</p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="!unassignedRequests.length"
        @click="autoAssignConfirmOpen = true; modalError = ''"
      >
        <UserRoundCheck :size="16" aria-hidden="true" />
        Tự động phân công ({{ unassignedRequests.length }})
      </button>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article v-for="reviewer in activeReviewers" :key="reviewer.id" class="rounded-xl border border-slate-200 bg-white p-4">
        <p class="text-sm font-semibold text-navy">{{ reviewer.fullName }}</p>
        <p class="mt-1 text-xs text-muted">{{ reviewer.expertise }}</p>
        <div class="mt-3 flex justify-between text-xs text-muted">
          <span>{{ reviewer.reviewedCourses }} đã kiểm duyệt</span>
          <span>{{ getAdminReviewerWorkload(reviewer.id) }} đang phụ trách</span>
        </div>
      </article>
    </section>

    <section v-if="autoAssignSummary" class="rounded-xl border border-primary/20 bg-primary/5 p-4" role="status">
      <h3 class="text-sm font-semibold text-navy">Kết quả phân công tự động</h3>
      <p class="mt-1 text-sm text-muted">
        Đã phân công {{ autoAssignSummary.assigned.length }} yêu cầu.
        {{ autoAssignSummary.unassigned.length }} yêu cầu chưa được phân công do thiếu Reviewer khớp danh mục và chuyên môn.
      </p>
      <ul v-if="autoAssignSummary.unassigned.length" class="mt-3 space-y-1.5 text-sm text-navy">
        <li v-for="request in autoAssignSummary.unassigned" :key="request.itemId">
          {{ request.title }} · {{ request.category || 'Chưa có danh mục' }} — {{ request.reason }}
        </li>
      </ul>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(240px,1fr)_180px_210px]">
        <SearchInput v-model="query" label="Tìm yêu cầu" placeholder="Tên nội dung, mã, người cung cấp..." />
        <label class="sr-only" for="assignment-type">Lọc loại nội dung</label>
        <select id="assignment-type" v-model="typeFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả nội dung</option>
          <option value="course">Khóa học</option>
          <option value="material">Tài liệu</option>
        </select>
        <label class="sr-only" for="assignment-status">Lọc trạng thái kiểm duyệt</label>
        <select id="assignment-status" v-model="statusFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Mọi trạng thái</option>
          <option value="ChoKiemDuyet">Chờ kiểm duyệt</option>
          <option value="DangKiemDuyet">Đang kiểm duyệt</option>
          <option value="YeuCauChinhSua">Yêu cầu chỉnh sửa</option>
        </select>
      </div>

      <div v-if="visibleRequests.length" class="overflow-x-auto">
        <table class="w-full min-w-[900px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Yêu cầu</th>
              <th scope="col" class="px-4 py-3 font-semibold">Loại</th>
              <th scope="col" class="px-4 py-3 font-semibold">Danh mục</th>
              <th scope="col" class="px-4 py-3 font-semibold">Người cung cấp</th>
              <th scope="col" class="px-4 py-3 font-semibold">Ngày gửi</th>
              <th scope="col" class="px-4 py-3 font-semibold">Trạng thái</th>
              <th scope="col" class="px-4 py-3 font-semibold">Reviewer</th>
              <th scope="col" class="px-4 py-3 text-right font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="request in visibleRequests" :key="request.id">
              <th scope="row" class="max-w-64 px-4 py-3.5">
                <span class="block line-clamp-2 font-semibold text-navy">{{ request.title }}</span>
                <span class="mt-1 block text-xs font-normal text-muted">{{ request.id }}</span>
              </th>
              <td class="px-4 py-3.5 text-muted">{{ request.itemType === 'course' ? 'Khóa học' : 'Tài liệu' }}</td>
              <td class="px-4 py-3.5 text-muted">{{ request.category || 'Chưa có danh mục' }}</td>
              <td class="px-4 py-3.5 text-muted">{{ request.creator }}</td>
              <td class="whitespace-nowrap px-4 py-3.5 text-muted">{{ formatDate(request.submittedAt) }}</td>
              <td class="px-4 py-3.5"><span class="rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-muted">{{ statusLabel(request.status) }}</span></td>
              <td class="px-4 py-3.5 text-muted">{{ request.reviewerName || 'Chưa phân công' }}</td>
              <td class="px-4 py-3.5 text-right">
                <button type="button" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:opacity-90" @click="openAssignment(request)">
                  <UserRoundCheck :size="14" aria-hidden="true" /> {{ request.reviewerName ? 'Đổi Reviewer' : 'Phân công' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="Không có yêu cầu cần phân công" description="Khi có nội dung chờ xử lý, yêu cầu sẽ xuất hiện tại đây." />
      <PaginationControls v-if="filteredRequests.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredRequests.length" />
    </section>

    <AdminModal
      :open="modalOpen"
      mode="form"
      :title="selectedRequest?.reviewerName ? 'Thay đổi Reviewer phụ trách' : 'Phân công Reviewer'"
      :description="selectedRequest?.title || ''"
      :record="modalRecord"
      :fields="assignmentFields"
      save-label="Xác nhận phân công"
      :error="modalError"
      @close="modalOpen = false"
      @save="saveAssignment"
    />
    <AdminModal
      :open="autoAssignConfirmOpen"
      mode="confirm"
      title="Tự động phân công Reviewer"
      description="Các yêu cầu chưa được phân công sẽ được ghép theo danh mục với chuyên môn của Reviewer đang hoạt động."
      confirm-label="Bắt đầu phân công"
      :error="modalError"
      @close="autoAssignConfirmOpen = false"
      @confirm="runAutomaticAssignment"
    >
      <p>Chỉ phân công khi có Reviewer khớp danh mục. Yêu cầu không có chuyên gia phù hợp sẽ giữ trạng thái chưa phân công; tải công việc được cân bằng trong nhóm Reviewer phù hợp.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
