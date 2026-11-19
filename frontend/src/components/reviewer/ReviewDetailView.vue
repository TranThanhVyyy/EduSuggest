<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { REVIEWABLE_STATUSES } from '@/constant/reviewStatus'
import CourseReviewPreview from '@/components/reviewer/CourseReviewPreview.vue'
import MaterialReviewPreview from '@/components/reviewer/MaterialReviewPreview.vue'
import ReviewActionModal from '@/components/reviewer/ReviewActionModal.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getReviewItem, submitReviewDecision } from '@/service/reviewerService'

const props = defineProps({
  kind: { type: String, required: true },
})

const route = useRoute()
const item = ref(null)
const loadError = ref('')
const actionError = ref('')
const actionModalOpen = ref(false)
const selectedAction = ref('')
const toastMessage = ref('')

const isCourse = computed(() => props.kind === 'course')
const queueRoute = computed(() => ({
  name: isCourse.value ? 'reviewer-courses' : 'reviewer-materials',
}))
const pageTitle = computed(() => (isCourse.value ? 'Chi tiết kiểm duyệt khóa học' : 'Chi tiết kiểm duyệt tài liệu'))
const canReview = computed(() => item.value && REVIEWABLE_STATUSES.includes(item.value.status))

watch(
  () => route.params.id,
  (id) => {
    loadError.value = ''
    item.value = null
    try {
      item.value = getReviewItem(props.kind, String(id))
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : 'Không thể tải nội dung.'
    }
  },
  { immediate: true },
)

function formatDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value))
}

function startAction(action) {
  actionError.value = ''
  selectedAction.value = action
  actionModalOpen.value = true
}

function confirmAction({ action, note }) {
  try {
    item.value = submitReviewDecision(props.kind, item.value.id, action, note)
    toastMessage.value = 'Kết quả kiểm duyệt đã được lưu trong phiên làm việc.'
    actionModalOpen.value = false
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : 'Không thể cập nhật kết quả kiểm duyệt.'
    actionModalOpen.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <RouterLink :to="queueRoute" class="inline-flex items-center gap-2 text-sm font-semibold text-muted transition hover:text-primary">
      <ArrowLeft :size="17" aria-hidden="true" /> Quay lại danh sách
    </RouterLink>

    <section v-if="loadError" class="rounded-2xl border border-slate-200 bg-white p-6" role="alert">
      <h2 class="font-bold text-navy">{{ pageTitle }}</h2>
      <p class="mt-2 text-sm text-muted">{{ loadError }}</p>
      <RouterLink :to="queueRoute" class="mt-4 inline-flex rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white">Về danh sách</RouterLink>
    </section>

    <template v-else-if="item">
      <section class="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="min-w-0">
          <p class="text-sm text-muted">{{ pageTitle }}</p>
          <h2 class="mt-1 break-words text-2xl font-bold tracking-tight text-navy">{{ item.title }}</h2>
          <p class="mt-2 text-sm text-muted">Gửi ngày {{ formatDate(item.submittedAt) }}</p>
        </div>
        <StatusBadge :status="item.status" />
      </section>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.8fr)]">
        <CourseReviewPreview v-if="isCourse" :item="item" />
        <MaterialReviewPreview v-else :item="item" />

        <aside class="space-y-5">
          <section class="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 class="font-bold text-navy">Thông tin người tạo</h3>
            <p class="mt-4 text-sm font-semibold text-navy">{{ item.creator }}</p>
            <p class="mt-1 break-all text-sm text-muted">{{ item.creatorEmail }}</p>
            <div class="mt-4 border-t border-slate-100 pt-4">
              <p class="text-xs font-medium uppercase tracking-wide text-muted">{{ isCourse ? 'Danh mục' : 'Loại tài liệu' }}</p>
              <p class="mt-1 text-sm font-semibold text-navy">{{ isCourse ? item.category : item.documentType }}</p>
            </div>
            <div class="mt-4 border-t border-slate-100 pt-4">
              <p class="text-xs font-medium uppercase tracking-wide text-muted">Ngày gửi</p>
              <p class="mt-1 text-sm font-semibold text-navy">{{ formatDate(item.submittedAt) }}</p>
            </div>
            <div v-if="!isCourse" class="mt-4 border-t border-slate-100 pt-4">
              <p class="text-xs font-medium uppercase tracking-wide text-muted">Tệp</p>
              <p class="mt-1 break-all text-sm font-semibold text-navy">{{ item.fileName || 'Chưa có tệp' }}</p>
            </div>
          </section>

          <section class="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 class="font-bold text-navy">Kết quả kiểm duyệt</h3>
            <p class="mt-1 text-sm leading-6 text-muted">Ghi nhận quyết định và phản hồi cho người tạo.</p>
            <p v-if="actionError" class="mt-3 rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ actionError }}</p>
            <p v-if="item.reviewNote" class="mt-3 rounded-xl bg-background p-3 text-sm leading-6 text-muted">{{ item.reviewNote }}</p>
            <div v-if="canReview" class="mt-4 grid gap-2">
              <button type="button" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary" @click="startAction('approve')">
                Phê duyệt
              </button>
              <button type="button" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy transition hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-primary" @click="startAction('requestChanges')">
                Yêu cầu chỉnh sửa
              </button>
              <button type="button" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-muted transition hover:border-navy hover:text-navy focus-visible:outline-2 focus-visible:outline-navy" @click="startAction('reject')">
                Từ chối
              </button>
            </div>
            <p v-else class="mt-4 rounded-xl bg-background p-3 text-sm text-muted">Nội dung đã được xử lý và không còn thao tác kiểm duyệt.</p>
          </section>
        </aside>
      </div>
    </template>

    <ReviewActionModal
      :open="actionModalOpen"
      :action="selectedAction"
      :item-title="item?.title"
      :item-description="item?.description"
      :item-kind="isCourse ? 'Khóa học' : 'Tài liệu'"
      @close="actionModalOpen = false"
      @confirm="confirmAction"
    />
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
