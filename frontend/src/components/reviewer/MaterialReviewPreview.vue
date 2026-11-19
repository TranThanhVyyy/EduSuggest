<script setup>
import { computed } from 'vue'
import { FileText, Paperclip } from 'lucide-vue-next'
import ResourcePreview from '@/components/reviewer/ResourcePreview.vue'

const props = defineProps({
  item: { type: Object, required: true },
})

const previewResource = computed(() => {
  const item = props.item
  const hasPreviewData = Boolean(
    item.fileName
    || item.fileUrl
    || item.url
    || item.text
    || item.textContent
    || item.content,
  )

  return hasPreviewData ? item : null
})

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return 'Chưa có dữ liệu'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`
}

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Chưa có dữ liệu'
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function relatedTitle(value) {
  if (typeof value === 'string') return value || 'Chưa có dữ liệu'
  return value?.title || 'Chưa có dữ liệu'
}
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="flex items-start gap-3">
        <FileText class="mt-0.5 shrink-0 text-primary" :size="20" aria-hidden="true" />
        <div class="min-w-0">
          <h3 class="break-words text-lg font-bold text-navy">{{ item.title }}</h3>
          <p class="mt-2 whitespace-pre-line text-sm leading-7 text-muted">{{ item.description || 'Chưa có mô tả tài liệu.' }}</p>
        </div>
      </div>

      <dl class="mt-5 grid gap-x-5 gap-y-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Tên tài liệu</dt>
          <dd class="mt-1 break-all text-sm font-semibold text-navy">{{ item.fileName || 'Chưa có tệp' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Người đăng</dt>
          <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ item.creator || 'Chưa có dữ liệu' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Loại tài liệu</dt>
          <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ item.documentType || 'Chưa có dữ liệu' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Định dạng file</dt>
          <dd class="mt-1 break-all text-sm font-semibold text-navy">{{ item.mimeType || 'Chưa có dữ liệu' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Dung lượng</dt>
          <dd class="mt-1 text-sm font-semibold text-navy">{{ formatBytes(item.fileSizeBytes) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Ngày tải lên</dt>
          <dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(item.uploadedAt) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Danh mục liên quan</dt>
          <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ item.category || 'Chưa có dữ liệu' }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Ngày gửi kiểm duyệt</dt>
          <dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(item.submittedAt) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Khóa học liên quan</dt>
          <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ relatedTitle(item.relatedCourse) }}</dd>
        </div>
        <div>
          <dt class="text-xs font-medium uppercase tracking-wide text-muted">Bài giảng liên quan</dt>
          <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ relatedTitle(item.relatedLesson) }}</dd>
        </div>
      </dl>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="mb-4 flex items-center gap-2">
        <Paperclip class="text-primary" :size="18" aria-hidden="true" />
        <div>
          <h3 class="font-bold text-navy">Xem trước tài liệu</h3>
          <p class="mt-1 text-sm text-muted">Trình xem phù hợp sẽ được chọn theo MIME type hoặc định dạng tệp.</p>
        </div>
      </div>
      <ResourcePreview :resource="previewResource" />
    </section>
  </div>
</template>
