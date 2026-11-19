<script setup>
import { computed, ref, watch } from 'vue'
import { BookOpen, ChevronLeft, ChevronRight, Clock3, FileText, Image, Paperclip } from 'lucide-vue-next'
import ResourcePreview from '@/components/reviewer/ResourcePreview.vue'

const props = defineProps({
  item: { type: Object, required: true },
})

const selectedLectureIndex = ref(0)
const selectedAttachmentIndex = ref(0)

const lectures = computed(() => (Array.isArray(props.item.lectures) ? props.item.lectures : []))
const attachments = computed(() => (Array.isArray(props.item.attachments) ? props.item.attachments : []))
const selectedLecture = computed(() => lectures.value[selectedLectureIndex.value] || null)
const selectedAttachment = computed(() => attachments.value[selectedAttachmentIndex.value] || null)

watch(
  () => props.item.id,
  () => {
    selectedLectureIndex.value = 0
    selectedAttachmentIndex.value = 0
  },
)

function selectLecture(index) {
  selectedLectureIndex.value = index
}

function previousLecture() {
  if (selectedLectureIndex.value > 0) selectedLectureIndex.value -= 1
}

function nextLecture() {
  if (selectedLectureIndex.value < lectures.value.length - 1) selectedLectureIndex.value += 1
}

function getFileName(resource) {
  return typeof resource === 'string' ? resource : resource?.fileName || resource?.name || 'Tài liệu'
}

function getFileFormat(resource) {
  if (typeof resource !== 'string' && (resource?.mimeType || resource?.contentType)) {
    return resource.mimeType || resource.contentType
  }

  const fileName = getFileName(resource)
  const extension = fileName.includes('.') ? fileName.split('.').pop() : ''
  return extension ? extension.toUpperCase() : 'Chưa có dữ liệu'
}

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

function formatPrice(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Chưa có dữ liệu'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value)
}

function attachmentValue(attachment, key) {
  if (typeof attachment === 'string') return ''
  return attachment?.[key] ?? ''
}

function hasLessonAttachmentData(lecture) {
  return Array.isArray(lecture.attachments)
}
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.4fr)]">
        <div v-if="item.coverImageUrl" class="min-w-0">
          <ResourcePreview :resource="{ type: 'image', url: item.coverImageUrl, name: 'Ảnh đại diện khóa học' }" />
        </div>
        <div v-else class="flex min-h-44 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-background p-5 text-center" role="status">
          <Image class="text-muted" :size="26" aria-hidden="true" />
          <p class="mt-2 text-sm font-semibold text-navy">Chưa có ảnh đại diện</p>
          <p class="mt-1 text-xs text-muted">Không có ảnh thực tế để xem trước.</p>
        </div>

        <div class="min-w-0">
          <h3 class="text-lg font-bold text-navy">Thông tin tổng quan khóa học</h3>
          <p class="mt-3 whitespace-pre-line text-sm leading-7 text-muted">{{ item.description || 'Chưa có mô tả khóa học.' }}</p>
          <dl class="mt-5 grid gap-x-5 gap-y-4 sm:grid-cols-2">
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Danh mục</dt>
              <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ item.category || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Người cung cấp</dt>
              <dd class="mt-1 break-words text-sm font-semibold text-navy">{{ item.provider || item.creator || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Đối tượng học viên</dt>
              <dd class="mt-1 break-words text-sm leading-6 text-navy">{{ item.audience || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Yêu cầu đầu vào</dt>
              <dd class="mt-1 break-words text-sm leading-6 text-navy">{{ item.entryRequirements || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Giá khóa học</dt>
              <dd class="mt-1 text-sm font-semibold text-navy">{{ formatPrice(item.price) }}</dd>
            </div>
            <div>
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Thời lượng khóa học</dt>
              <dd class="mt-1 text-sm font-semibold text-navy">{{ item.duration || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div class="sm:col-span-2">
              <dt class="text-xs font-medium uppercase tracking-wide text-muted">Ngày gửi kiểm duyệt</dt>
              <dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(item.submittedAt) }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div class="mt-6 grid gap-5 border-t border-slate-100 pt-5 md:grid-cols-2">
        <section>
          <h4 class="text-sm font-bold text-navy">Mục tiêu khóa học</h4>
          <ul v-if="item.objectives?.length" class="mt-3 space-y-2">
            <li v-for="objective in item.objectives" :key="objective" class="flex items-start gap-2 text-sm leading-6 text-muted">
              <span class="mt-2 size-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true"></span>
              {{ objective }}
            </li>
          </ul>
          <p v-else class="mt-2 text-sm text-muted">Chưa có dữ liệu mục tiêu.</p>
        </section>
        <section>
          <h4 class="text-sm font-bold text-navy">Kiến thức và kỹ năng đạt được</h4>
          <ul v-if="item.skillsLearned?.length" class="mt-3 space-y-2">
            <li v-for="skill in item.skillsLearned" :key="skill" class="flex items-start gap-2 text-sm leading-6 text-muted">
              <span class="mt-2 size-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true"></span>
              {{ skill }}
            </li>
          </ul>
          <p v-else class="mt-2 text-sm text-muted">Chưa có dữ liệu kiến thức hoặc kỹ năng đầu ra.</p>
        </section>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="flex items-start gap-3">
        <BookOpen class="mt-0.5 shrink-0 text-primary" :size="19" aria-hidden="true" />
        <div>
          <h3 class="font-bold text-navy">Chương trình và nội dung bài giảng</h3>
          <p class="mt-1 text-sm text-muted">Chọn từng bài học để kiểm tra mô tả, trạng thái và nội dung thực tế nếu được cung cấp.</p>
        </div>
      </div>

      <div v-if="!lectures.length" class="mt-4 rounded-xl border border-dashed border-slate-300 bg-background p-5 text-sm text-muted" role="status">
        Khóa học chưa có dữ liệu bài giảng.
      </div>

      <div v-else class="mt-5 grid min-w-0 gap-4 lg:grid-cols-[minmax(220px,0.75fr)_minmax(0,1.5fr)]">
        <details open class="min-w-0 rounded-xl border border-slate-200">
          <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-navy">Danh sách bài học ({{ lectures.length }})</summary>
          <ol class="max-h-[34rem] space-y-1 overflow-y-auto border-t border-slate-100 p-2">
            <li v-for="(lecture, index) in lectures" :key="lecture.id || lecture.title || index">
              <button
                type="button"
                class="w-full rounded-lg p-3 text-left transition focus-visible:outline-2 focus-visible:outline-primary"
                :class="selectedLectureIndex === index ? 'bg-primary/10 text-primary' : 'text-navy hover:bg-background'"
                :aria-current="selectedLectureIndex === index ? 'true' : undefined"
                @click="selectLecture(index)"
              >
                <span class="flex items-start gap-3">
                  <span class="flex size-7 shrink-0 items-center justify-center rounded-md bg-white text-xs font-bold text-muted">{{ String(lecture.order ?? index + 1).padStart(2, '0') }}</span>
                  <span class="min-w-0 flex-1">
                    <span class="block break-words text-sm font-semibold">{{ lecture.title || 'Bài học chưa có tên' }}</span>
                    <span class="mt-1 block text-xs text-muted">{{ lecture.chapterTitle || 'Chưa phân chương' }}</span>
                  </span>
                </span>
              </button>
            </li>
          </ol>
        </details>

        <section v-if="selectedLecture" class="min-w-0 space-y-4">
          <div class="rounded-xl border border-slate-200 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-xs font-semibold uppercase tracking-wide text-muted">Bài {{ String(selectedLecture.order ?? selectedLectureIndex + 1).padStart(2, '0') }} / {{ lectures.length }}</p>
              <div class="flex gap-2">
                <button type="button" class="flex size-9 items-center justify-center rounded-lg border border-slate-200 text-navy hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40" aria-label="Bài học trước" :disabled="selectedLectureIndex === 0" @click="previousLecture">
                  <ChevronLeft :size="18" aria-hidden="true" />
                </button>
                <button type="button" class="flex size-9 items-center justify-center rounded-lg border border-slate-200 text-navy hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40" aria-label="Bài học tiếp theo" :disabled="selectedLectureIndex === lectures.length - 1" @click="nextLecture">
                  <ChevronRight :size="18" aria-hidden="true" />
                </button>
              </div>
            </div>
            <h4 class="mt-3 break-words text-lg font-bold text-navy">{{ selectedLecture.title || 'Bài học chưa có tên' }}</h4>
            <p class="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{{ selectedLecture.description || selectedLecture.summary || 'Chưa có mô tả bài giảng.' }}</p>
            <dl class="mt-4 grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3">
              <div>
                <dt class="text-xs text-muted">Thời lượng</dt>
                <dd class="mt-1 inline-flex items-center gap-1 text-sm font-medium text-navy">
                  <Clock3 :size="14" aria-hidden="true" /> {{ selectedLecture.duration || 'Chưa có dữ liệu' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-muted">Loại nội dung</dt>
                <dd class="mt-1 break-words text-sm font-medium text-navy">{{ selectedLecture.contentType || selectedLecture.mimeType || 'Chưa có dữ liệu' }}</dd>
              </div>
              <div>
                <dt class="text-xs text-muted">Trạng thái nội dung</dt>
                <dd class="mt-1 text-sm font-medium text-navy">{{ selectedLecture.status || 'Chưa có dữ liệu' }}</dd>
              </div>
            </dl>
          </div>

          <div>
            <h5 class="mb-2 text-sm font-bold text-navy">Nội dung bài giảng</h5>
            <ResourcePreview :resource="selectedLecture.content ?? selectedLecture.preview ?? null" />
          </div>

          <div v-if="selectedLecture.attachments?.length">
            <h5 class="mb-2 text-sm font-bold text-navy">Tài liệu của bài giảng</h5>
            <details v-for="(attachment, index) in selectedLecture.attachments" :key="attachment.id || attachment.fileName || index" class="mb-2 rounded-xl border border-slate-200">
              <summary class="cursor-pointer break-words px-4 py-3 text-sm font-semibold text-navy">{{ getFileName(attachment) }}</summary>
              <div class="space-y-3 border-t border-slate-100 p-3">
                <dl class="grid gap-2 text-xs sm:grid-cols-2">
                  <div><dt class="text-muted">Định dạng</dt><dd class="mt-0.5 break-all font-medium text-navy">{{ getFileFormat(attachment) }}</dd></div>
                  <div><dt class="text-muted">Dung lượng</dt><dd class="mt-0.5 font-medium text-navy">{{ formatBytes(attachmentValue(attachment, 'sizeBytes')) }}</dd></div>
                </dl>
                <ResourcePreview :resource="attachment" />
              </div>
            </details>
          </div>
          <p v-else-if="hasLessonAttachmentData(selectedLecture)" class="rounded-lg bg-background p-3 text-sm text-muted">Bài giảng chưa có tài liệu đính kèm.</p>
          <p v-else class="rounded-lg bg-background p-3 text-sm text-muted">Chưa có dữ liệu về tài liệu đính kèm của bài giảng.</p>
        </section>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="flex items-center gap-2">
        <Paperclip class="text-primary" :size="18" aria-hidden="true" />
        <h3 class="font-bold text-navy">Tài liệu liên quan đến khóa học</h3>
      </div>

      <div v-if="!attachments.length" class="mt-4 rounded-xl border border-dashed border-slate-300 bg-background p-5 text-sm text-muted" role="status">
        Khóa học chưa có tài liệu đính kèm.
      </div>

      <div v-else class="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(210px,0.7fr)_minmax(0,1.5fr)]">
        <details open class="min-w-0 rounded-xl border border-slate-200">
          <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-navy">Danh sách tài liệu ({{ attachments.length }})</summary>
          <ul class="space-y-1 border-t border-slate-100 p-2">
            <li v-for="(attachment, index) in attachments" :key="attachment.id || getFileName(attachment)">
              <button
                type="button"
                class="flex w-full items-start gap-2 rounded-lg p-3 text-left text-sm transition hover:bg-background focus-visible:outline-2 focus-visible:outline-primary"
                :class="selectedAttachmentIndex === index ? 'bg-primary/10 text-primary' : 'text-navy'"
                :aria-current="selectedAttachmentIndex === index ? 'true' : undefined"
                @click="selectedAttachmentIndex = index"
              >
                <FileText class="mt-0.5 shrink-0" :size="16" aria-hidden="true" />
                <span class="break-words font-medium">{{ getFileName(attachment) }}</span>
              </button>
            </li>
          </ul>
        </details>

        <section v-if="selectedAttachment" class="min-w-0 space-y-3">
          <div>
            <h4 class="break-words font-semibold text-navy">{{ getFileName(selectedAttachment) }}</h4>
            <p v-if="attachmentValue(selectedAttachment, 'description')" class="mt-1 text-sm leading-6 text-muted">{{ attachmentValue(selectedAttachment, 'description') }}</p>
          </div>
          <dl class="grid gap-x-4 gap-y-3 rounded-xl bg-background p-4 text-sm sm:grid-cols-2">
            <div><dt class="text-xs text-muted">Định dạng</dt><dd class="mt-1 break-all font-medium text-navy">{{ getFileFormat(selectedAttachment) }}</dd></div>
            <div><dt class="text-xs text-muted">Dung lượng</dt><dd class="mt-1 font-medium text-navy">{{ formatBytes(attachmentValue(selectedAttachment, 'sizeBytes')) }}</dd></div>
            <div><dt class="text-xs text-muted">Người tải lên</dt><dd class="mt-1 break-words font-medium text-navy">{{ attachmentValue(selectedAttachment, 'uploadedBy') || 'Chưa có dữ liệu' }}</dd></div>
            <div><dt class="text-xs text-muted">Ngày tải lên</dt><dd class="mt-1 font-medium text-navy">{{ formatDate(attachmentValue(selectedAttachment, 'uploadedAt')) }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-xs text-muted">Bài giảng liên quan</dt><dd class="mt-1 break-words font-medium text-navy">{{ attachmentValue(selectedAttachment, 'lessonTitle') || 'Chưa có dữ liệu' }}</dd></div>
          </dl>
          <ResourcePreview :resource="selectedAttachment" />
        </section>
      </div>
    </section>
  </div>
</template>
