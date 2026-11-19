<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { ArrowLeft, ArrowRight, Check, Plus, Trash2, Upload } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  getProviderCategories,
  getProviderCourse,
  saveProviderCourse,
  submitProviderCourseForReview,
  validateProviderCourse,
  createProviderCourse,
} from '@/service/providerService'

const route = useRoute()
const router = useRouter()
const steps = ['Thông tin cơ bản', 'Cấu trúc khóa học', 'Nội dung bài học', 'Tài liệu', 'Xem trước']
const categories = getProviderCategories()
const step = ref(Number(route.meta.providerInitialStep) || 0)
const savedObjectUrls = ref(new Set())
const generatedObjectUrls = new Set()
const courseId = ref(String(route.params.id || ''))
const originalCourse = ref(null)
const errorMessage = ref('')
const toastMessage = ref('')
const submitConfirmOpen = ref(false)
const form = reactive({
  title: '',
  category: '',
  coverImageUrl: '',
  coverImageName: '',
  shortDescription: '',
  description: '',
  objectives: '',
  audience: '',
  prerequisites: '',
  outcomes: '',
  estimatedDuration: '',
  chapters: [],
  materials: [],
})

const courseLoadError = ref('')
const isEditable = computed(() => !originalCourse.value || [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(originalCourse.value.status))
const isResubmission = computed(() => originalCourse.value
  && [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(originalCourse.value.status))
const validationIssues = computed(() => validateProviderCourse(form))
const checklist = computed(() => [
  { label: 'Thông tin cơ bản và danh mục', complete: Boolean(form.title.trim() && form.category && form.shortDescription.trim() && form.description.trim()) },
  { label: 'Ảnh đại diện', complete: Boolean(form.coverImageUrl) },
  { label: 'Mục tiêu, đối tượng, kiến thức đầu vào và kết quả', complete: Boolean(form.objectives.trim() && form.audience.trim() && form.prerequisites.trim() && form.outcomes.trim()) },
  { label: 'Thời lượng dự kiến', complete: Boolean(form.estimatedDuration.trim()) },
  { label: 'Có chương và bài học', complete: Boolean(form.chapters.length && form.chapters.every((chapter) => chapter.title.trim() && chapter.lessons.length)) },
  { label: 'Nội dung bài học', complete: Boolean(form.chapters.length && form.chapters.every((chapter) => chapter.lessons.every((lesson) => lesson.title.trim() && (lesson.content.trim() || lesson.video?.url)))) },
])

if (courseId.value) {
  try {
    originalCourse.value = getProviderCourse(courseId.value)
    Object.assign(form, JSON.parse(JSON.stringify(originalCourse.value)))
  } catch (error) {
    courseLoadError.value = error instanceof Error ? error.message : 'Không thể tải khóa học.'
  }
}

function collectObjectUrls(course) {
  const urls = new Set()
  if (course.coverImageUrl?.startsWith('blob:')) urls.add(course.coverImageUrl)
  for (const chapter of course.chapters || []) {
    for (const lesson of chapter.lessons || []) {
      if (lesson.video?.url?.startsWith('blob:')) urls.add(lesson.video.url)
      if (lesson.video?.thumbnailUrl?.startsWith('blob:')) urls.add(lesson.video.thumbnailUrl)
    }
  }
  for (const material of course.materials || []) {
    if (material.fileUrl?.startsWith('blob:')) urls.add(material.fileUrl)
  }
  return urls
}

function createLocalUrl(file) {
  const url = URL.createObjectURL(file)
  generatedObjectUrls.add(url)
  return url
}

function setCover(event) {
  const file = event.target.files?.[0]
  if (!file) return
  form.coverImageUrl = createLocalUrl(file)
  form.coverImageName = file.name
  errorMessage.value = ''
}

function persistForm() {
  if (!courseId.value) {
    const course = createProviderCourse()
    courseId.value = course.id
  }
  const saved = saveProviderCourse(courseId.value, {
    title: form.title,
    category: form.category,
    coverImageUrl: form.coverImageUrl,
    coverImageName: form.coverImageName,
    shortDescription: form.shortDescription,
    description: form.description,
    objectives: form.objectives,
    audience: form.audience,
    prerequisites: form.prerequisites,
    outcomes: form.outcomes,
    estimatedDuration: form.estimatedDuration,
    chapters: form.chapters,
    materials: form.materials,
  })
  originalCourse.value = saved
  savedObjectUrls.value = collectObjectUrls(form)
  return saved
}

function saveDraft() {
  try {
    persistForm()
    toastMessage.value = 'Đã lưu bản nháp trong phiên hiện tại.'
    errorMessage.value = ''
    if (route.name === 'provider-course-create') {
      router.replace({ name: 'provider-course-edit', params: { id: courseId.value } })
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể lưu bản nháp.'
  }
}

function validateStep() {
  const problems = []
  if (step.value === 0) {
    if (!form.title.trim()) problems.push('Nhập tên khóa học.')
    if (!form.category) problems.push('Chọn danh mục.')
    if (!form.shortDescription.trim()) problems.push('Nhập mô tả ngắn.')
    if (!form.description.trim()) problems.push('Nhập mô tả chi tiết.')
  } else if (step.value === 1) {
    if (!form.chapters.length) problems.push('Thêm ít nhất một chương.')
    if (form.chapters.some((chapter) => !chapter.title.trim())) problems.push('Nhập tên cho tất cả chương.')
    if (form.chapters.some((chapter) => !chapter.lessons.length)) problems.push('Mỗi chương cần có ít nhất một bài học.')
    if (form.chapters.some((chapter) => chapter.lessons.some((lesson) => !lesson.title.trim()))) problems.push('Nhập tên cho tất cả bài học.')
  } else if (step.value === 2) {
    if (form.chapters.some((chapter) => chapter.lessons.some((lesson) => !lesson.content.trim() && !lesson.video?.url))) {
      problems.push('Mỗi bài học cần có nội dung văn bản hoặc video thực tế.')
    }
  }
  return problems
}

function goNext() {
  const problems = validateStep()
  if (problems.length) {
    errorMessage.value = problems.join(' ')
    return
  }
  errorMessage.value = ''
  step.value = Math.min(step.value + 1, steps.length - 1)
}

function goBack() {
  errorMessage.value = ''
  step.value = Math.max(step.value - 1, 0)
}

function addChapter() {
  form.chapters.push({
    id: `CH-TEMP-${Date.now()}`,
    title: `Chương ${form.chapters.length + 1}`,
    description: '',
    lessons: [],
  })
}

function removeChapter(chapterIndex) {
  form.chapters.splice(chapterIndex, 1)
  form.materials.forEach((material) => {
    if (!form.chapters.some((chapter) => chapter.lessons.some((lesson) => lesson.id === material.lessonId))) {
      material.lessonId = ''
    }
  })
}

function moveItem(items, index, direction) {
  const nextIndex = index + direction
  if (nextIndex < 0 || nextIndex >= items.length) return
  ;[items[index], items[nextIndex]] = [items[nextIndex], items[index]]
}

function addLesson(chapter) {
  chapter.lessons.push({
    id: `LESSON-TEMP-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
    title: '',
    description: '',
    duration: '',
    content: '',
    video: null,
  })
}

function removeLesson(chapter, lessonIndex) {
  const [removed] = chapter.lessons.splice(lessonIndex, 1)
  form.materials.forEach((material) => {
    if (material.lessonId === removed?.id) material.lessonId = ''
  })
}

function ensureVideo(lesson) {
  if (!lesson.video) {
    lesson.video = { title: '', url: '', duration: '', description: '', thumbnailUrl: '' }
  }
}

function setLessonVideo(event, lesson) {
  const file = event.target.files?.[0]
  if (!file) return
  ensureVideo(lesson)
  lesson.video.title ||= file.name
  lesson.video.url = createLocalUrl(file)
  lesson.video.localFileName = file.name
}

function removeVideo(lesson) {
  lesson.video = null
}

function addMaterial() {
  form.materials.push({
    id: `MAT-TEMP-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
    title: '',
    description: '',
    documentType: '',
    fileName: '',
    mimeType: '',
    sizeBytes: null,
    fileUrl: '',
    lessonId: '',
  })
}

function setMaterialFile(event, material) {
  const file = event.target.files?.[0]
  if (!file) return
  material.fileUrl = createLocalUrl(file)
  material.fileName = file.name
  material.mimeType = file.type
  material.sizeBytes = file.size
  if (!material.title) material.title = file.name.replace(/\.[^.]+$/, '')
}

function removeMaterial(index) {
  form.materials.splice(index, 1)
}

function submitForReview() {
  try {
    const wasResubmission = isResubmission.value
    const saved = persistForm()
    submitProviderCourseForReview(saved.id)
    toastMessage.value = wasResubmission
      ? 'Đã gửi lại khóa học để kiểm duyệt trong phiên hiện tại.'
      : 'Đã gửi khóa học để kiểm duyệt trong phiên hiện tại.'
    submitConfirmOpen.value = false
    router.push({ name: 'provider-course-detail', params: { id: saved.id } })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể gửi kiểm duyệt.'
    submitConfirmOpen.value = false
  }
}

function formatBytes(bytes) {
  if (!bytes) return 'Chưa có dung lượng'
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onBeforeUnmount(() => {
  for (const url of generatedObjectUrls) {
    if (!savedObjectUrls.value.has(url)) URL.revokeObjectURL(url)
  }
})
</script>

<template>
  <div v-if="courseLoadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không thể mở trình soạn khóa học</h2>
    <p class="mt-2 text-sm text-muted">{{ courseLoadError }}</p>
    <RouterLink :to="{ name: 'provider-courses' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink>
  </div>
  <div v-else-if="!isEditable" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Khóa học hiện không thể chỉnh sửa</h2>
    <p class="mt-2 text-sm text-muted">Trạng thái hiện tại: {{ PROVIDER_STATUS_LABELS[originalCourse?.status] }}. Nội dung đã gửi hoặc đã được xử lý cần tuân theo quy trình Backend.</p>
    <RouterLink :to="{ name: 'provider-course-detail', params: { id: courseId } }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Xem khóa học</RouterLink>
  </div>
  <div v-else class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">{{ originalCourse ? 'Cập nhật khóa học' : 'Trình tạo khóa học' }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ form.title || 'Khóa học mới' }}</h2>
        <p class="mt-2 text-sm text-muted">{{ isResubmission ? 'Cập nhật nội dung theo yêu cầu; phản hồi trước đó vẫn được lưu trong hồ sơ.' : 'Hoàn thiện theo từng bước. Có thể lưu bản nháp và quay lại sau.' }}</p>
      </div>
      <button type="button" class="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background" @click="saveDraft">Lưu bản nháp</button>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <ol class="grid gap-2 sm:grid-cols-5" aria-label="Các bước tạo khóa học">
        <li v-for="(label, index) in steps" :key="label">
          <button type="button" class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-semibold transition" :class="step === index ? 'bg-primary text-white' : index < step ? 'bg-accent/10 text-accent' : 'bg-background text-muted'" :aria-current="step === index ? 'step' : undefined" @click="index <= step && (step = index)">
            <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-white/20">{{ index < step ? '✓' : index + 1 }}</span>
            <span>{{ label }}</span>
          </button>
        </li>
      </ol>

      <div v-if="step === 0" class="mt-6 grid gap-4 md:grid-cols-2">
        <label class="text-sm font-semibold text-navy md:col-span-2">Tên khóa học *
          <input v-model="form.title" maxlength="160" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Ví dụ: Vue.js 3 từ cơ bản đến thực chiến">
        </label>
        <label class="text-sm font-semibold text-navy">Danh mục *
          <select v-model="form.category" class="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
            <option value="">Chọn danh mục</option>
            <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
          </select>
        </label>
        <label class="text-sm font-semibold text-navy">Thời lượng dự kiến *
          <input v-model="form.estimatedDuration" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Ví dụ: 8 giờ">
        </label>
        <label class="text-sm font-semibold text-navy md:col-span-2">Ảnh đại diện *
          <span class="mt-1.5 flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-slate-300 p-3">
            <img v-if="form.coverImageUrl" :src="form.coverImageUrl" alt="Ảnh đại diện khóa học" class="size-16 rounded-lg object-cover">
            <span class="min-w-0 flex-1 text-xs font-normal text-muted">{{ form.coverImageName || 'Chọn ảnh thực tế; tệp chỉ có hiệu lực trong phiên này.' }}</span>
            <span class="inline-flex items-center gap-2 rounded-lg bg-background px-3 py-2 text-xs font-semibold text-navy"><Upload :size="14" aria-hidden="true" /> Chọn ảnh
              <input type="file" accept="image/*" class="sr-only" @change="setCover">
            </span>
          </span>
        </label>
        <label class="text-sm font-semibold text-navy md:col-span-2">Mô tả ngắn *
          <textarea v-model="form.shortDescription" rows="2" maxlength="300" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Tóm tắt nội dung khóa học"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy md:col-span-2">Mô tả chi tiết *
          <textarea v-model="form.description" rows="4" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Mô tả chi tiết khóa học"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy">Mục tiêu khóa học *
          <textarea v-model="form.objectives" rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Mỗi mục tiêu một dòng"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy">Đối tượng học viên *
          <textarea v-model="form.audience" rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy">Kiến thức đầu vào *
          <textarea v-model="form.prerequisites" rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Ghi rõ nếu không yêu cầu"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy">Kết quả đạt được *
          <textarea v-model="form.outcomes" rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
      </div>

      <div v-else-if="step === 1" class="mt-6 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div><h3 class="font-bold text-navy">Chương và bài học</h3><p class="mt-1 text-xs text-muted">Thứ tự hiện tại là thứ tự học; dùng mũi tên để sắp xếp.</p></div>
          <button type="button" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-primary hover:bg-background" @click="addChapter"><Plus :size="16" aria-hidden="true" /> Thêm chương</button>
        </div>
        <article v-for="(chapter, chapterIndex) in form.chapters" :key="chapter.id" class="rounded-xl border border-slate-200 p-4">
          <div class="flex flex-wrap items-start gap-2">
            <div class="grid flex-1 gap-3 sm:grid-cols-2">
              <label class="text-xs font-semibold text-muted">Tên chương
                <input v-model="chapter.title" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary">
              </label>
              <label class="text-xs font-semibold text-muted">Mô tả chương
                <input v-model="chapter.description" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary">
              </label>
            </div>
            <div class="flex gap-1">
              <button type="button" class="rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-navy disabled:opacity-40" :disabled="chapterIndex === 0" aria-label="Chuyển chương lên" @click="moveItem(form.chapters, chapterIndex, -1)">↑</button>
              <button type="button" class="rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-navy disabled:opacity-40" :disabled="chapterIndex === form.chapters.length - 1" aria-label="Chuyển chương xuống" @click="moveItem(form.chapters, chapterIndex, 1)">↓</button>
              <button type="button" class="rounded-lg p-2 text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Xóa ${chapter.title}`" @click="removeChapter(chapterIndex)"><Trash2 :size="15" aria-hidden="true" /></button>
            </div>
          </div>
          <div class="mt-4 space-y-2">
            <div v-for="(lesson, lessonIndex) in chapter.lessons" :key="lesson.id" class="flex flex-wrap items-center gap-2 rounded-lg bg-background p-3">
              <span class="text-xs font-semibold text-muted">{{ lessonIndex + 1 }}.</span>
              <input v-model="lesson.title" class="min-w-40 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-primary" placeholder="Tên bài học">
              <input v-model="lesson.duration" class="w-32 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-primary" placeholder="Thời lượng">
              <button type="button" class="rounded-lg p-2 text-muted hover:text-primary disabled:opacity-40" :disabled="lessonIndex === 0" aria-label="Chuyển bài học lên" @click="moveItem(chapter.lessons, lessonIndex, -1)">↑</button>
              <button type="button" class="rounded-lg p-2 text-muted hover:text-primary disabled:opacity-40" :disabled="lessonIndex === chapter.lessons.length - 1" aria-label="Chuyển bài học xuống" @click="moveItem(chapter.lessons, lessonIndex, 1)">↓</button>
              <button type="button" class="rounded-lg p-2 text-muted hover:text-primary" aria-label="Xóa bài học" @click="removeLesson(chapter, lessonIndex)"><Trash2 :size="14" aria-hidden="true" /></button>
            </div>
          </div>
          <button type="button" class="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline" @click="addLesson(chapter)"><Plus :size="14" aria-hidden="true" /> Thêm bài học</button>
        </article>
        <p v-if="!form.chapters.length" class="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-muted">Chưa có chương. Thêm chương để xây dựng cấu trúc khóa học.</p>
      </div>

      <div v-else-if="step === 2" class="mt-6 space-y-4">
        <h3 class="font-bold text-navy">Nội dung bài học</h3>
        <details v-for="(lesson, index) in form.chapters.flatMap((chapter) => chapter.lessons.map((item) => ({ ...item, chapterTitle: chapter.title })))" :key="lesson.id" class="rounded-xl border border-slate-200 bg-white p-4" :open="index === 0">
          <summary class="cursor-pointer font-semibold text-navy">{{ lesson.title || 'Bài học chưa đặt tên' }} <span class="ml-1 text-xs font-normal text-muted">· {{ lesson.chapterTitle }}</span></summary>
          <div class="mt-4 grid gap-3">
            <label class="text-sm font-semibold text-navy">Mô tả bài học
              <textarea v-model="form.chapters.find((chapter) => chapter.lessons.some((item) => item.id === lesson.id)).lessons.find((item) => item.id === lesson.id).description" rows="2" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal outline-none focus:border-primary"></textarea>
            </label>
            <label class="text-sm font-semibold text-navy">Nội dung văn bản
              <textarea v-model="form.chapters.find((chapter) => chapter.lessons.some((item) => item.id === lesson.id)).lessons.find((item) => item.id === lesson.id).content" rows="5" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal outline-none focus:border-primary" placeholder="Nội dung thực tế của bài học"></textarea>
            </label>
            <div class="rounded-xl border border-slate-200 p-3">
              <p class="text-sm font-semibold text-navy">Video bài học</p>
              <div v-if="lesson.video?.url" class="mt-2">
                <video v-if="lesson.video.url.startsWith('blob:')" :src="lesson.video.url" controls class="max-h-64 w-full rounded-lg bg-navy"></video>
                <a v-else :href="lesson.video.url" target="_blank" rel="noopener noreferrer" class="mt-2 inline-flex text-sm font-semibold text-primary hover:underline">Mở video trong tab mới</a>
                <p class="mt-2 text-xs text-muted">{{ lesson.video.localFileName || lesson.video.title || lesson.video.url }}</p>
                <button type="button" class="mt-2 text-xs font-semibold text-primary hover:underline" @click="removeVideo(form.chapters.find((chapter) => chapter.lessons.some((item) => item.id === lesson.id)).lessons.find((item) => item.id === lesson.id))">Gỡ video</button>
              </div>
              <div v-else class="mt-2 flex flex-wrap items-center gap-3">
                <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background"><Upload :size="14" aria-hidden="true" /> Chọn video thật
                  <input type="file" accept="video/*" class="sr-only" @change="setLessonVideo($event, form.chapters.find((chapter) => chapter.lessons.some((item) => item.id === lesson.id)).lessons.find((item) => item.id === lesson.id))">
                </label>
                <span class="text-xs text-muted">Hoặc thêm URL video thực tế tại bước Quản lý video.</span>
              </div>
            </div>
          </div>
        </details>
        <p v-if="!form.chapters.some((chapter) => chapter.lessons.length)" class="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-muted">Thêm chương và bài học ở bước trước.</p>
      </div>

      <div v-else-if="step === 3" class="mt-6 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div><h3 class="font-bold text-navy">Tài liệu khóa học</h3><p class="mt-1 text-xs text-muted">Có thể gắn tài liệu cho toàn khóa học hoặc một bài học.</p></div>
          <button type="button" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-primary hover:bg-background" @click="addMaterial"><Plus :size="16" aria-hidden="true" /> Thêm tài liệu</button>
        </div>
        <article v-for="(material, index) in form.materials" :key="material.id" class="grid gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-2">
          <label class="text-xs font-semibold text-muted">Tên tài liệu
            <input v-model="material.title" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary">
          </label>
          <label class="text-xs font-semibold text-muted">Loại tài liệu
            <input v-model="material.documentType" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary" placeholder="E-book, slide, bài tập...">
          </label>
          <label class="text-xs font-semibold text-muted md:col-span-2">Mô tả
            <textarea v-model="material.description" rows="2" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary"></textarea>
          </label>
          <label class="text-xs font-semibold text-muted">Bài học liên quan
            <select v-model="material.lessonId" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-navy">
              <option value="">Tài liệu toàn khóa học</option>
              <option v-for="lesson in form.chapters.flatMap((chapter) => chapter.lessons)" :key="lesson.id" :value="lesson.id">{{ lesson.title || 'Bài học chưa đặt tên' }}</option>
            </select>
          </label>
          <div class="flex items-end justify-between gap-2">
            <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background"><Upload :size="14" aria-hidden="true" /> Chọn tệp thật
              <input type="file" class="sr-only" @change="setMaterialFile($event, material)">
            </label>
            <button type="button" class="rounded-lg p-2 text-muted hover:bg-primary/10 hover:text-primary" :aria-label="`Xóa tài liệu ${material.title}`" @click="removeMaterial(index)"><Trash2 :size="15" aria-hidden="true" /></button>
          </div>
          <p class="text-xs text-muted md:col-span-2">{{ material.fileName || 'Chưa chọn tệp' }} · {{ formatBytes(material.sizeBytes) }} · {{ material.mimeType || 'Chưa xác định định dạng' }}</p>
          <a v-if="material.fileUrl" :href="material.fileUrl" target="_blank" rel="noopener noreferrer" class="text-xs font-semibold text-primary hover:underline md:col-span-2">Mở tài liệu đã chọn</a>
        </article>
        <p v-if="!form.materials.length" class="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-muted">Chưa thêm tài liệu. Có thể bỏ qua bước này.</p>
      </div>

      <div v-else class="mt-6 space-y-5">
        <div>
          <h3 class="text-lg font-bold text-navy">Xem trước và kiểm tra điều kiện gửi</h3>
          <p class="mt-1 text-sm text-muted">Trạng thái kiểm duyệt không đồng nghĩa trạng thái công khai. Chỉ Backend mới có thể xác nhận trạng thái hiển thị.</p>
        </div>
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,0.7fr)]">
          <article class="rounded-xl border border-slate-200 p-4">
            <img v-if="form.coverImageUrl" :src="form.coverImageUrl" alt="Ảnh đại diện khóa học" class="mb-4 max-h-64 w-full rounded-lg object-cover">
            <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ form.category || 'Chưa chọn danh mục' }} · {{ form.estimatedDuration || 'Chưa có thời lượng' }}</p>
            <h4 class="mt-2 text-xl font-bold text-navy">{{ form.title || 'Tên khóa học' }}</h4>
            <p class="mt-2 text-sm text-muted">{{ form.shortDescription || 'Chưa có mô tả ngắn.' }}</p>
            <p class="mt-4 whitespace-pre-line text-sm leading-6 text-navy">{{ form.description || 'Chưa có mô tả chi tiết.' }}</p>
            <div class="mt-5 space-y-3">
              <section v-for="chapter in form.chapters" :key="chapter.id" class="rounded-lg bg-background p-3">
                <h5 class="font-semibold text-navy">{{ chapter.title }}</h5>
                <p v-if="chapter.description" class="mt-1 text-xs text-muted">{{ chapter.description }}</p>
                <ul class="mt-2 space-y-2">
                  <li v-for="lesson in chapter.lessons" :key="lesson.id" class="text-sm text-navy">
                    {{ lesson.title || 'Bài học chưa đặt tên' }} <span class="text-xs text-muted">· {{ lesson.duration || 'Chưa có thời lượng' }}</span>
                    <p v-if="lesson.content" class="mt-1 line-clamp-3 text-xs leading-5 text-muted">{{ lesson.content }}</p>
                    <p v-else-if="lesson.video?.url" class="mt-1 text-xs text-muted">Có video đã chọn: {{ lesson.video.localFileName || lesson.video.url }}</p>
                  </li>
                </ul>
              </section>
            </div>
            <p class="mt-4 text-xs text-muted">{{ form.materials.length }} tài liệu đính kèm</p>
          </article>
          <aside class="space-y-3">
            <section class="rounded-xl border border-slate-200 p-4">
              <h4 class="font-bold text-navy">Điều kiện gửi kiểm duyệt</h4>
              <ul class="mt-3 space-y-2">
                <li v-for="item in checklist" :key="item.label" class="flex gap-2 text-xs" :class="item.complete ? 'text-accent' : 'text-muted'">
                  <Check :size="15" class="mt-0.5 shrink-0" aria-hidden="true" />
                  <span>{{ item.label }}</span>
                </li>
              </ul>
              <p class="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-muted">Reviewer chưa được tự gán tại giao diện Provider. Việc phân công thuộc quy trình kiểm duyệt.</p>
            </section>
            <section class="rounded-xl border border-slate-200 bg-background p-4">
              <p class="text-xs font-semibold text-navy">Trạng thái hiện tại</p>
              <p class="mt-1 text-sm text-muted">{{ originalCourse ? PROVIDER_STATUS_LABELS[originalCourse.status] : 'Bản nháp chưa lưu' }}</p>
              <p class="mt-3 text-xs leading-5 text-muted">Provider không có thao tác phê duyệt hoặc công khai khóa học.</p>
            </section>
          </aside>
        </div>
      </div>

      <p v-if="errorMessage" class="mt-5 rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
      <div class="mt-6 flex flex-col-reverse justify-between gap-2 border-t border-slate-100 pt-4 sm:flex-row">
        <button type="button" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background" @click="step ? goBack() : router.push({ name: 'provider-courses' })">
          <ArrowLeft :size="16" aria-hidden="true" /> {{ step ? 'Quay lại' : 'Danh sách khóa học' }}
        </button>
        <div class="flex flex-col gap-2 sm:flex-row">
          <button v-if="step < steps.length - 1" type="button" class="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90" @click="goNext">Tiếp tục <ArrowRight :size="16" aria-hidden="true" /></button>
          <button v-else type="button" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="validationIssues.length > 0" @click="submitConfirmOpen = true">Gửi kiểm duyệt</button>
        </div>
      </div>
    </section>

    <AdminModal
      :open="submitConfirmOpen"
      mode="confirm"
      :title="isResubmission ? 'Xác nhận gửi lại kiểm duyệt' : 'Xác nhận gửi kiểm duyệt'"
      :description="form.title || 'Khóa học chưa đặt tên'"
      confirm-label="Xác nhận gửi"
      @close="submitConfirmOpen = false"
      @confirm="submitForReview"
    >
      <p>Khóa học sẽ chuyển sang trạng thái Chờ kiểm duyệt. Reviewer quyết định kết quả; thao tác này không phê duyệt hoặc công khai khóa học.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
