<script setup>
import { onMounted, ref } from 'vue'
import { ArrowLeft, Clock3 } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  PROVIDER_STATUS_LABELS,
} from '@/service/providerApiService'
import { loadProviderCourse, loadProviderReviews, mapProviderReview, providerErrorMessage } from '@/service/providerApiService'

const route = useRoute()
const courseId = String(route.params.id)
const course = ref(null)
const timeline = ref([])
const loadError = ref('')
const isLoading = ref(true)

onMounted(async () => {
  try {
    course.value = await loadProviderCourse(courseId)
    const reviews = await loadProviderReviews(courseId)
    timeline.value = reviews.map(mapProviderReview).map((review) => ({ action: review.action, detail: review.feedback, createdAt: review.createdAt }))
  } catch (error) {
    loadError.value = providerErrorMessage(error, 'Không thể tải tiến trình kiểm duyệt từ Backend.')
  } finally {
    isLoading.value = false
  }
})

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
</script>

<template>
  <div v-if="isLoading" class="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-muted" role="status">Đang tải tiến trình…</div>
  <div v-else-if="loadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không tìm thấy tiến trình</h2>
    <p class="mt-2 text-sm text-muted">{{ loadError }}</p>
  </div>
  <div v-else-if="course" class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Kiểm duyệt · {{ course.id }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ route.name === 'provider-course-feedback' ? 'Phản hồi Reviewer' : 'Chi tiết tiến trình kiểm duyệt' }}</h2>
        <p class="mt-2 text-sm text-muted">{{ course.title }}</p>
      </div>
      <RouterLink :to="{ name: 'provider-reviews' }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><ArrowLeft :size="15" aria-hidden="true" /> Danh sách kiểm duyệt</RouterLink>
    </section>

    <section class="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div><p class="text-xs text-muted">Trạng thái kiểm duyệt</p><p class="mt-1 text-lg font-bold text-navy">{{ PROVIDER_STATUS_LABELS[course.status] || course.status }}</p></div>
          <span class="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">{{ course.category || 'Chưa có danh mục' }}</span>
        </div>
        <dl class="mt-5 grid gap-4 sm:grid-cols-2">
          <div><dt class="text-xs text-muted">Ngày gửi</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(course.submittedAt) }}</dd></div>
          <div><dt class="text-xs text-muted">Reviewer phụ trách</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ course.reviewerName || 'Chưa có dữ liệu phân công' }}</dd></div>
          <div><dt class="text-xs text-muted">Ngày cập nhật</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(course.reviewedAt || course.updatedAt) }}</dd></div>
          <div><dt class="text-xs text-muted">Trạng thái hiển thị</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ course.visibility ? (course.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn') : 'Chưa có dữ liệu Backend' }}</dd></div>
        </dl>
        <section class="mt-6 rounded-xl border border-slate-200 bg-background p-4">
          <h3 class="font-bold text-navy">Nhận xét / lý do từ Reviewer</h3>
          <p class="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{{ course.reviewFeedback || 'Chưa có nhận xét được lưu cho khóa học này.' }}</p>
          <p class="mt-3 text-xs leading-5 text-muted">Không tự tạo lý do từ chối hoặc yêu cầu chỉnh sửa khi dữ liệu chưa có.</p>
        </section>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 class="font-bold text-navy">Các mốc có dữ liệu</h3>
        <ol v-if="timeline.length" class="mt-4 space-y-4">
          <li v-for="(event, index) in timeline" :key="`${event.action}-${index}`" class="flex gap-3">
            <span class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full" :class="index === timeline.length - 1 ? 'bg-primary/10 text-primary' : 'bg-background text-muted'"><Clock3 :size="15" aria-hidden="true" /></span>
            <div class="min-w-0">
              <p class="text-sm font-semibold text-navy">{{ event.action }}</p>
              <p v-if="event.detail" class="mt-1 whitespace-pre-line text-xs leading-5 text-muted">{{ event.detail }}</p>
              <p class="mt-1 text-xs text-muted">{{ formatDate(event.createdAt) }}</p>
            </div>
          </li>
        </ol>
        <p v-else class="mt-4 text-sm text-muted">Chưa có dữ liệu lịch sử.</p>
        <p class="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-muted">Việc phân công Reviewer và cập nhật trạng thái kiểm duyệt phải được xác nhận bởi Backend hoặc Admin.</p>
      </article>
    </section>
  </div>
</template>
