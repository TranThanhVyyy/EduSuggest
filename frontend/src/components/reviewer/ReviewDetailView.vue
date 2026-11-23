<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Check, FileText } from 'lucide-vue-next'
import { REVIEWABLE_STATUSES } from '@/constant/reviewStatus'
import ReviewActionModal from '@/components/reviewer/ReviewActionModal.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getExpertCourse, submitExpertCourseDecision } from '@/service/expertApiService'

const route = useRoute()
const props = defineProps({ kind: { type: String, required: true } })
const item = ref(null)
const loading = ref(false)
const loadError = ref('')
const actionError = ref('')
const actionModalOpen = ref(false)
const selectedAction = ref('')
const saving = ref(false)
const isCourse = computed(() => props.kind === 'course')
const canReview = computed(() => isCourse.value && item.value && REVIEWABLE_STATUSES.includes(item.value.status))
const queueRoute = computed(() => ({ name: isCourse.value ? 'reviewer-courses' : 'reviewer-materials' }))

async function loadCourse(id) {
  item.value = null
  loadError.value = ''
  if (!isCourse.value) {
    loadError.value = 'Backend hiện chưa cung cấp API chi tiết kiểm duyệt tài liệu.'
    return
  }
  loading.value = true
  try {
    item.value = await getExpertCourse(id)
  } catch (error) {
    loadError.value = error.response?.data?.detail || 'Không thể tải khóa học. Hãy quay lại danh sách hoặc thử lại.'
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, loadCourse, { immediate: true })

function startAction(action) {
  actionError.value = ''
  selectedAction.value = action
  actionModalOpen.value = true
}

async function confirmAction({ action, note }) {
  if (!item.value || saving.value) return
  saving.value = true
  actionError.value = ''
  try {
    const updatedCourse = await submitExpertCourseDecision(item.value.id, action, note)
    item.value = {
      ...item.value,
      ...updatedCourse,
      // The decision endpoint returns CourseResponse, not CourseDetailResponse.
      lectures: item.value.lectures,
      attachments: item.value.attachments,
    }
    actionModalOpen.value = false
  } catch (error) {
    actionError.value = error.response?.data?.detail || 'Không thể lưu quyết định kiểm duyệt. Hãy thử lại.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="space-y-6">
    <RouterLink :to="queueRoute" class="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"><ArrowLeft :size="16" aria-hidden="true" /> Quay lại danh sách</RouterLink>
    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải khóa học…</p>
    <section v-else-if="loadError" class="max-w-2xl border-l-2 border-accent py-1 pl-4" role="alert"><h1 class="ui-page-title">Không thể mở nội dung</h1><p class="mt-2 text-sm leading-6 text-muted">{{ loadError }}</p></section>
    <template v-else-if="item">
      <header class="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div><p class="ui-eyebrow">Khóa học #{{ item.id }}</p><h1 class="ui-page-title mt-2">{{ item.title }}</h1><p class="mt-2 max-w-3xl whitespace-pre-line text-sm leading-6 text-muted">{{ item.description || 'Chưa có mô tả.' }}</p></div>
        <StatusBadge :status="item.status" />
      </header>
      <dl class="grid gap-x-8 gap-y-4 border-b border-border pb-5 sm:grid-cols-3"><div><dt class="text-xs text-muted">Danh mục</dt><dd class="mt-1 text-sm font-medium text-navy">{{ item.category || 'Chưa có dữ liệu' }}</dd></div><div><dt class="text-xs text-muted">Nhà cung cấp</dt><dd class="mt-1 text-sm font-medium text-navy">{{ item.provider || 'Chưa có dữ liệu' }}</dd></div><div><dt class="text-xs text-muted">Giá</dt><dd class="mt-1 text-sm font-medium text-navy">{{ item.price == null ? 'Chưa có dữ liệu' : new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(item.price) }}</dd></div></dl>
      <section><h2 class="text-lg font-medium text-navy">Bài học ({{ item.lectures.length }})</h2><ol v-if="item.lectures.length" class="mt-3 divide-y divide-border border-y border-border"><li v-for="(lesson, index) in item.lectures" :key="lesson.id" class="py-4"><h3 class="font-medium text-navy">{{ index + 1 }}. {{ lesson.title }}</h3><p v-if="lesson.content" class="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{{ lesson.content }}</p><ul v-if="lesson.attachments.length" class="mt-3 space-y-2"><li v-for="file in lesson.attachments" :key="file.name" class="flex items-center gap-2 text-sm text-muted"><FileText :size="15" aria-hidden="true" /> {{ file.name }} <a v-if="file.url" :href="file.url" target="_blank" rel="noreferrer" class="text-secondary underline">Mở tài liệu</a></li></ul></li></ol><p v-else class="mt-3 text-sm text-muted">Khóa học chưa có bài học.</p></section>
      <section class="border-t border-border pt-5"><h2 class="text-lg font-medium text-navy">Quyết định kiểm duyệt</h2><p v-if="item.reviewNote" class="mt-2 text-sm leading-6 text-muted">{{ item.reviewNote }}</p><p v-if="actionError" class="mt-3 text-sm text-danger" role="alert">{{ actionError }}</p><div v-if="canReview" class="mt-4 flex flex-wrap gap-2"><button :disabled="saving" class="inline-flex items-center gap-2 bg-primary px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60" @click="startAction('approve')"><Check :size="16" aria-hidden="true" /> Phê duyệt</button><button :disabled="saving" class="border border-border px-4 py-2.5 text-sm font-medium text-navy disabled:opacity-60" @click="startAction('requestChanges')">Yêu cầu chỉnh sửa</button><button :disabled="saving" class="border border-border px-4 py-2.5 text-sm font-medium text-navy disabled:opacity-60" @click="startAction('reject')">Từ chối</button></div><p v-else class="mt-2 text-sm text-muted">Khóa học đã được xử lý.</p></section>
    </template>
    <ReviewActionModal :open="actionModalOpen" :action="selectedAction" :item-title="item?.title" :item-description="item?.description" :saving="saving" :error-message="actionError" item-kind="Khóa học" @close="actionModalOpen = false" @confirm="confirmAction" />
  </main>
</template>
