<script setup>
import { computed, ref } from 'vue'
import { ArrowLeft, BookOpen, FileText, FileVideo, Pencil, Send } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  getProviderCourse,
  getProviderCourseTimeline,
  submitProviderCourseForReview,
  validateProviderCourse,
} from '@/service/providerService'

const route = useRoute()
const router = useRouter()
const courseId = String(route.params.id)
const loadError = ref('')
const course = ref(null)
const timeline = ref([])
const submitConfirmOpen = ref(false)
const modalError = ref('')
const toastMessage = ref('')

try {
  course.value = getProviderCourse(courseId)
  timeline.value = getProviderCourseTimeline(courseId)
} catch (error) {
  loadError.value = error instanceof Error ? error.message : 'Không thể tải khóa học.'
}

const isEditable = computed(() => course.value && [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(course.value.status))
const canSubmit = computed(() => isEditable.value && validateProviderCourse(course.value).length === 0)
const lessonCount = computed(() => course.value?.chapters.reduce((sum, chapter) => sum + chapter.lessons.length, 0) || 0)

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function statusClass(status) {
  if (status === PROVIDER_STATUS.approved) return 'bg-accent/10 text-accent'
  if ([PROVIDER_STATUS.pending, PROVIDER_STATUS.pendingAssignment, PROVIDER_STATUS.reviewing].includes(status)) return 'bg-primary/10 text-primary'
  if ([PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(status)) return 'bg-slate-100 text-navy'
  return 'bg-background text-muted'
}

function confirmSubmit() {
  try {
    submitProviderCourseForReview(courseId)
    course.value = getProviderCourse(courseId)
    timeline.value = getProviderCourseTimeline(courseId)
    toastMessage.value = 'Đã gửi khóa học để kiểm duyệt trong phiên hiện tại.'
    submitConfirmOpen.value = false
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể gửi kiểm duyệt.'
  }
}
</script>

<template>
  <div v-if="loadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không tìm thấy khóa học</h2>
    <p class="mt-2 text-sm text-muted">{{ loadError }}</p>
    <RouterLink :to="{ name: 'provider-courses' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink>
  </div>
  <div v-else-if="course" class="space-y-5">
    <section class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex min-w-0 items-start gap-4">
        <img v-if="course.coverImageUrl" :src="course.coverImageUrl" :alt="`Ảnh đại diện ${course.title}`" class="size-20 shrink-0 rounded-xl object-cover sm:size-28">
        <span v-else class="flex size-20 shrink-0 items-center justify-center rounded-xl bg-white text-muted sm:size-28"><BookOpen :size="28" aria-hidden="true" /></span>
        <div class="min-w-0">
          <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ course.category || 'Chưa chọn danh mục' }} · {{ course.id }}</p>
          <h2 class="mt-2 text-2xl font-bold tracking-tight text-navy">{{ course.title || 'Khóa học chưa đặt tên' }}</h2>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">{{ course.shortDescription || course.description }}</p>
          <span class="mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold" :class="statusClass(course.status)">{{ PROVIDER_STATUS_LABELS[course.status] || course.status }}</span>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <RouterLink :to="{ name: 'provider-courses' }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><ArrowLeft :size="15" aria-hidden="true" /> Danh sách</RouterLink>
        <RouterLink v-if="isEditable" :to="{ name: 'provider-course-edit', params: { id: course.id } }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><Pencil :size="15" aria-hidden="true" /> Chỉnh sửa</RouterLink>
        <button v-if="isEditable" type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="!canSubmit" @click="submitConfirmOpen = true"><Send :size="15" aria-hidden="true" /> Gửi kiểm duyệt</button>
      </div>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Tạo ngày</p><p class="mt-1 text-sm font-semibold text-navy">{{ formatDate(course.createdAt) }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Gửi kiểm duyệt</p><p class="mt-1 text-sm font-semibold text-navy">{{ formatDate(course.submittedAt) }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Cấu trúc</p><p class="mt-1 text-sm font-semibold text-navy">{{ course.chapters.length }} chương · {{ lessonCount }} bài học</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Trạng thái hiển thị</p><p class="mt-1 text-sm font-semibold text-navy">{{ course.status === PROVIDER_STATUS.approved ? (course.visibility ? (course.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn') : 'Chưa có dữ liệu Backend') : 'Chưa công khai' }}</p></article>
    </section>

    <section class="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
      <div class="space-y-5">
        <article class="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 class="text-lg font-bold text-navy">Thông tin khóa học</h3>
          <p class="mt-3 whitespace-pre-line text-sm leading-6 text-muted">{{ course.description || 'Chưa có mô tả chi tiết.' }}</p>
          <dl class="mt-5 grid gap-4 sm:grid-cols-2">
            <div><dt class="text-xs font-semibold text-muted">Mục tiêu</dt><dd class="mt-1 whitespace-pre-line text-sm text-navy">{{ course.objectives || 'Chưa có dữ liệu.' }}</dd></div>
            <div><dt class="text-xs font-semibold text-muted">Đối tượng học viên</dt><dd class="mt-1 whitespace-pre-line text-sm text-navy">{{ course.audience || 'Chưa có dữ liệu.' }}</dd></div>
            <div><dt class="text-xs font-semibold text-muted">Kiến thức đầu vào</dt><dd class="mt-1 whitespace-pre-line text-sm text-navy">{{ course.prerequisites || 'Chưa có dữ liệu.' }}</dd></div>
            <div><dt class="text-xs font-semibold text-muted">Kết quả đạt được</dt><dd class="mt-1 whitespace-pre-line text-sm text-navy">{{ course.outcomes || 'Chưa có dữ liệu.' }}</dd></div>
          </dl>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-5">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div><h3 class="text-lg font-bold text-navy">Chương trình học</h3><p class="mt-1 text-xs text-muted">{{ course.estimatedDuration || 'Chưa có thời lượng dự kiến' }}</p></div>
            <RouterLink :to="{ name: 'provider-lessons', params: { id: course.id } }" class="text-sm font-semibold text-primary hover:underline">Quản lý bài học</RouterLink>
          </div>
          <div v-if="course.chapters.length" class="mt-4 space-y-3">
            <details v-for="(chapter, index) in course.chapters" :key="chapter.id" class="rounded-xl border border-slate-200 p-4" :open="index === 0">
              <summary class="cursor-pointer font-semibold text-navy">Chương {{ index + 1 }} · {{ chapter.title }}</summary>
              <p v-if="chapter.description" class="mt-2 text-sm text-muted">{{ chapter.description }}</p>
              <ol class="mt-3 space-y-3">
                <li v-for="(lesson, lessonIndex) in chapter.lessons" :key="lesson.id" class="rounded-lg bg-background p-3">
                  <p class="text-sm font-semibold text-navy">{{ lessonIndex + 1 }}. {{ lesson.title }}</p>
                  <p v-if="lesson.description" class="mt-1 text-xs text-muted">{{ lesson.description }}</p>
                  <p class="mt-2 whitespace-pre-line text-sm leading-6 text-navy">{{ lesson.content || 'Chưa có nội dung văn bản.' }}</p>
                  <video v-if="lesson.video?.url?.startsWith('blob:')" :src="lesson.video.url" controls class="mt-3 max-h-64 w-full rounded-lg bg-navy"></video>
                  <a v-else-if="lesson.video?.url" :href="lesson.video.url" target="_blank" rel="noopener noreferrer" class="mt-2 inline-flex items-center gap-2 text-xs font-semibold text-primary hover:underline"><FileVideo :size="14" aria-hidden="true" /> Mở video</a>
                  <span class="mt-2 block text-xs text-muted">{{ lesson.duration || 'Chưa có thời lượng' }}</span>
                </li>
              </ol>
              <p v-if="!chapter.lessons.length" class="mt-3 text-sm text-muted">Chương chưa có bài học.</p>
            </details>
          </div>
          <p v-else class="mt-4 rounded-xl border border-dashed border-slate-200 p-4 text-sm text-muted">Khóa học chưa có chương.</p>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-5">
          <div class="flex items-center justify-between gap-3">
            <div><h3 class="text-lg font-bold text-navy">Tài liệu đính kèm</h3><p class="mt-1 text-xs text-muted">Tệp chỉ tồn tại trong phiên demo nếu được chọn từ máy.</p></div>
            <RouterLink :to="{ name: 'provider-materials', params: { id: course.id } }" class="text-sm font-semibold text-primary hover:underline">Quản lý tài liệu</RouterLink>
          </div>
          <ul v-if="course.materials.length" class="mt-4 divide-y divide-slate-100">
            <li v-for="material in course.materials" :key="material.id" class="flex flex-wrap items-center justify-between gap-2 py-3">
              <span class="flex min-w-0 items-center gap-2"><FileText :size="16" class="shrink-0 text-muted" aria-hidden="true" /><span class="truncate text-sm font-semibold text-navy">{{ material.title }}</span></span>
              <a v-if="material.fileUrl" :href="material.fileUrl" target="_blank" rel="noopener noreferrer" class="text-xs font-semibold text-primary hover:underline">Mở tệp</a>
              <span v-else class="text-xs text-muted">Chưa có tệp xem trước</span>
            </li>
          </ul>
          <p v-else class="mt-4 text-sm text-muted">Chưa có tài liệu đính kèm.</p>
        </article>
      </div>

      <aside class="space-y-5">
        <article class="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 class="font-bold text-navy">Tiến trình kiểm duyệt</h3>
          <p class="mt-1 text-xs text-muted">Reviewer phụ trách: {{ course.reviewerName || 'Chưa có dữ liệu phân công' }}</p>
          <ol class="mt-4 space-y-4">
            <li v-for="(entry, index) in timeline" :key="`${entry.action}-${index}`" class="flex gap-3">
              <span class="mt-1 size-2.5 shrink-0 rounded-full" :class="index === timeline.length - 1 ? 'bg-primary' : 'bg-slate-300'"></span>
              <div><p class="text-sm font-semibold text-navy">{{ entry.action }}</p><p v-if="entry.detail" class="mt-1 text-xs text-muted">{{ entry.detail }}</p><p class="mt-1 text-xs text-muted">{{ formatDate(entry.createdAt) }}</p></div>
            </li>
          </ol>
          <p v-if="!timeline.length" class="mt-4 text-sm text-muted">Chưa có dữ liệu lịch sử kiểm duyệt.</p>
        </article>

        <article v-if="[PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(course.status)" class="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 class="font-bold text-navy">Phản hồi Reviewer</h3>
          <p class="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{{ course.reviewFeedback || 'Chưa có nhận xét hoặc lý do được lưu trong dữ liệu hiện tại.' }}</p>
          <RouterLink :to="{ name: 'provider-course-feedback', params: { id: course.id } }" class="mt-3 inline-flex text-sm font-semibold text-primary hover:underline">Xem phản hồi</RouterLink>
        </article>

        <article class="rounded-2xl border border-primary/15 bg-primary/5 p-5">
          <h3 class="font-bold text-navy">Quản lý nội dung</h3>
          <div class="mt-3 flex flex-wrap gap-2">
            <RouterLink :to="{ name: 'provider-videos', params: { id: course.id } }" class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-navy hover:bg-background">Video</RouterLink>
            <RouterLink :to="{ name: 'provider-materials', params: { id: course.id } }" class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-navy hover:bg-background">Tài liệu</RouterLink>
            <RouterLink :to="{ name: 'provider-reviews' }" class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-navy hover:bg-background">Theo dõi kiểm duyệt</RouterLink>
          </div>
          <p class="mt-3 text-xs leading-5 text-muted">Không có thao tác công khai. Tình trạng hiển thị cần được Backend xác nhận.</p>
        </article>
      </aside>
    </section>

    <AdminModal
      :open="submitConfirmOpen"
      mode="confirm"
      title="Xác nhận gửi kiểm duyệt"
      :description="course.title"
      confirm-label="Gửi kiểm duyệt"
      :error="modalError"
      @close="submitConfirmOpen = false"
      @confirm="confirmSubmit"
    >
      <p>Khóa học sẽ được chuyển sang trạng thái chờ kiểm duyệt. Provider không thể tự phê duyệt hoặc công khai nội dung.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
