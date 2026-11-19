<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { ArrowLeft, FileVideo, Plus, Save, Trash2, Upload } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  getProviderCourse,
  saveProviderMaterial,
  saveProviderVideo,
  deleteProviderMaterial,
} from '@/service/providerService'

const route = useRoute()
const courseId = String(route.params.id)
const assetType = route.name === 'provider-videos' ? 'video' : 'material'
const course = ref(null)
const loadError = ref('')
const errorMessage = ref('')
const toastMessage = ref('')
const videoDrafts = reactive({})
const generatedObjectUrls = new Set()
const materialFormOpen = ref(false)
const editingMaterialId = ref('')
const materialForm = reactive({
  title: '',
  documentType: '',
  description: '',
  fileName: '',
  mimeType: '',
  sizeBytes: null,
  fileUrl: '',
  lessonId: '',
})

function refresh() {
  try {
    course.value = JSON.parse(JSON.stringify(getProviderCourse(courseId)))
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Không thể tải nội dung khóa học.'
  }
}

refresh()

const canEdit = computed(() => course.value && [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(course.value.status))
const lessons = computed(() => course.value?.chapters.flatMap((chapter) =>
  chapter.lessons.map((lesson) => ({ ...lesson, chapterId: chapter.id, chapterTitle: chapter.title })),
) || [])

function videoDraft(lesson) {
  if (!videoDrafts[lesson.id]) {
    videoDrafts[lesson.id] = {
      title: lesson.video?.title || '',
      url: lesson.video?.url || '',
      localFileName: lesson.video?.localFileName || '',
      duration: lesson.video?.duration || '',
      description: lesson.video?.description || '',
      thumbnailUrl: lesson.video?.thumbnailUrl || '',
    }
  }
  return videoDrafts[lesson.id]
}

function createLocalUrl(file) {
  const url = URL.createObjectURL(file)
  generatedObjectUrls.add(url)
  return url
}

function setVideoFile(event, draft) {
  const file = event.target.files?.[0]
  if (!file) return
  if (generatedObjectUrls.has(draft.url)) {
    URL.revokeObjectURL(draft.url)
    generatedObjectUrls.delete(draft.url)
  }
  draft.url = createLocalUrl(file)
  draft.localFileName = file.name
  if (!draft.title) draft.title = file.name.replace(/\.[^.]+$/, '')
}

function setThumbnail(event, draft) {
  const file = event.target.files?.[0]
  if (!file) return
  if (generatedObjectUrls.has(draft.thumbnailUrl)) {
    URL.revokeObjectURL(draft.thumbnailUrl)
    generatedObjectUrls.delete(draft.thumbnailUrl)
  }
  draft.thumbnailUrl = createLocalUrl(file)
}

function saveVideo(lesson) {
  try {
    const draft = videoDraft(lesson)
    saveProviderVideo(courseId, lesson.chapterId, lesson.id, draft)
    errorMessage.value = ''
    toastMessage.value = draft.url ? 'Đã lưu thông tin video trong phiên.' : 'Đã gỡ video trong phiên.'
    refresh()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể cập nhật video.'
  }
}

function clearVideo(lesson) {
  try {
    saveProviderVideo(courseId, lesson.chapterId, lesson.id, {})
    delete videoDrafts[lesson.id]
    refresh()
    errorMessage.value = ''
    toastMessage.value = 'Đã gỡ video trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể gỡ video.'
  }
}

function openNewMaterial() {
  editingMaterialId.value = ''
  Object.assign(materialForm, {
    title: '',
    documentType: '',
    description: '',
    fileName: '',
    mimeType: '',
    sizeBytes: null,
    fileUrl: '',
    lessonId: '',
  })
  materialFormOpen.value = true
  errorMessage.value = ''
}

function openEditMaterial(material) {
  editingMaterialId.value = material.id
  Object.assign(materialForm, material)
  materialFormOpen.value = true
  errorMessage.value = ''
}

function setMaterialFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (generatedObjectUrls.has(materialForm.fileUrl)) {
    URL.revokeObjectURL(materialForm.fileUrl)
    generatedObjectUrls.delete(materialForm.fileUrl)
  }
  materialForm.fileUrl = createLocalUrl(file)
  materialForm.fileName = file.name
  materialForm.mimeType = file.type
  materialForm.sizeBytes = file.size
  if (!materialForm.title) materialForm.title = file.name.replace(/\.[^.]+$/, '')
}

function saveMaterial() {
  try {
    saveProviderMaterial(courseId, {
      ...materialForm,
      ...(editingMaterialId.value ? { id: editingMaterialId.value } : {}),
    })
    refresh()
    materialFormOpen.value = false
    errorMessage.value = ''
    toastMessage.value = 'Đã lưu tài liệu trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể lưu tài liệu.'
  }
}

function removeMaterial(material) {
  try {
    deleteProviderMaterial(courseId, material.id)
    refresh()
    errorMessage.value = ''
    toastMessage.value = 'Đã xóa tài liệu trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể xóa tài liệu.'
  }
}

function fileKind(material) {
  const mime = material.mimeType || ''
  if (mime === 'application/pdf' || material.fileName?.toLowerCase().endsWith('.pdf')) return 'pdf'
  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  return 'download'
}

function formatBytes(bytes) {
  if (!bytes) return 'Chưa có dung lượng'
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onBeforeUnmount(() => {
  const savedUrls = new Set()
  if (course.value) {
    for (const chapter of course.value.chapters) {
      for (const lesson of chapter.lessons) {
        if (lesson.video?.url?.startsWith('blob:')) savedUrls.add(lesson.video.url)
        if (lesson.video?.thumbnailUrl?.startsWith('blob:')) savedUrls.add(lesson.video.thumbnailUrl)
      }
    }
    for (const material of course.value.materials) {
      if (material.fileUrl?.startsWith('blob:')) savedUrls.add(material.fileUrl)
    }
  }
  for (const url of generatedObjectUrls) {
    if (!savedUrls.has(url)) URL.revokeObjectURL(url)
  }
})
</script>

<template>
  <div v-if="loadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không thể mở quản lý nội dung</h2>
    <p class="mt-2 text-sm text-muted">{{ loadError }}</p>
    <RouterLink :to="{ name: 'provider-courses' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink>
  </div>
  <div v-else-if="course" class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Quản lý nội dung · {{ course.id }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ assetType === 'video' ? 'Video bài học' : 'Tài liệu khóa học' }}</h2>
        <p class="mt-2 text-sm text-muted">{{ course.title }} · Tệp được chọn chỉ tồn tại trong phiên demo.</p>
      </div>
      <div class="flex gap-2">
        <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><ArrowLeft :size="15" aria-hidden="true" /> Chi tiết khóa học</RouterLink>
        <button v-if="assetType === 'material'" type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50" :disabled="!canEdit" @click="openNewMaterial"><Plus :size="16" aria-hidden="true" /> Thêm tài liệu</button>
      </div>
    </section>

    <p v-if="!canEdit" class="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-muted">Khóa học đang ở trạng thái {{ course.status }} nên nội dung không thể thay đổi. Video/tài liệu không được tự công khai.</p>
    <p v-if="errorMessage" class="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>

    <section v-if="assetType === 'video'" class="space-y-4">
      <article v-for="lesson in lessons" :key="lesson.id" class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ lesson.chapterTitle }}</p><h3 class="mt-1 font-bold text-navy">{{ lesson.title || 'Bài học chưa đặt tên' }}</h3><p class="mt-1 text-xs text-muted">{{ lesson.duration || 'Chưa có thời lượng bài học' }}</p></div>
          <FileVideo :size="20" class="text-muted" aria-hidden="true" />
        </div>
        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <label class="text-xs font-semibold text-muted">Tên video
            <input v-model="videoDraft(lesson).title" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background">
          </label>
          <label class="text-xs font-semibold text-muted">Thời lượng
            <input v-model="videoDraft(lesson).duration" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background" placeholder="Ví dụ: 12 phút">
          </label>
          <label class="text-xs font-semibold text-muted md:col-span-2">URL video thực tế
            <input v-model="videoDraft(lesson).url" :disabled="!canEdit" type="url" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background" placeholder="https://...">
          </label>
          <label class="text-xs font-semibold text-muted md:col-span-2">Mô tả video
            <textarea v-model="videoDraft(lesson).description" :disabled="!canEdit" rows="2" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background"></textarea>
          </label>
          <div class="flex flex-wrap items-center gap-2 md:col-span-2">
            <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background" :class="!canEdit ? 'pointer-events-none opacity-50' : ''"><Upload :size="14" aria-hidden="true" /> Chọn tệp video
              <input type="file" accept="video/*" class="sr-only" :disabled="!canEdit" @change="setVideoFile($event, videoDraft(lesson))">
            </label>
            <span class="text-xs text-muted">{{ videoDraft(lesson).localFileName || (videoDraft(lesson).url ? 'Đã có URL video' : 'Chưa có video') }}</span>
            <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background" :class="!canEdit ? 'pointer-events-none opacity-50' : ''">Ảnh thumbnail
              <input type="file" accept="image/*" class="sr-only" :disabled="!canEdit" @change="setThumbnail($event, videoDraft(lesson))">
            </label>
          </div>
          <img v-if="videoDraft(lesson).thumbnailUrl" :src="videoDraft(lesson).thumbnailUrl" alt="Thumbnail video" class="max-h-40 rounded-lg object-cover md:col-span-2">
        </div>
        <video v-if="videoDraft(lesson).url?.startsWith('blob:')" :src="videoDraft(lesson).url" controls class="mt-4 max-h-72 w-full rounded-xl bg-navy"></video>
        <a v-else-if="videoDraft(lesson).url" :href="videoDraft(lesson).url" target="_blank" rel="noopener noreferrer" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Mở URL video trong tab mới</a>
        <p v-else class="mt-3 text-xs text-muted">Chưa có video xem trước. Không tạo URL video tự động.</p>
        <div class="mt-4 flex justify-end gap-2">
          <button v-if="lesson.video" type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background disabled:opacity-50" :disabled="!canEdit" @click="clearVideo(lesson)">Gỡ video</button>
          <button type="button" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50" :disabled="!canEdit" @click="saveVideo(lesson)"><Save :size="14" aria-hidden="true" /> Lưu video</button>
        </div>
      </article>
      <p v-if="!lessons.length" class="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">Khóa học chưa có bài học để gắn video. Thêm bài học trước trong mục Chương và bài học.</p>
    </section>

    <section v-else class="space-y-4">
      <article v-for="material in course.materials" :key="material.id" class="rounded-2xl border border-slate-200 bg-white p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate font-bold text-navy">{{ material.title }}</h3>
            <p class="mt-1 text-xs text-muted">{{ material.documentType || 'Chưa phân loại' }} · {{ material.fileName || 'Chưa chọn tệp' }} · {{ formatBytes(material.sizeBytes) }}</p>
            <p class="mt-1 text-xs text-muted">{{ material.description || 'Chưa có mô tả.' }}</p>
            <p class="mt-1 text-xs text-muted">{{ material.lessonId ? `Bài học: ${lessons.find((lesson) => lesson.id === material.lessonId)?.title || 'Không tìm thấy'}` : 'Tài liệu toàn khóa học' }}</p>
          </div>
          <div class="flex shrink-0 gap-2">
            <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background disabled:opacity-50" :disabled="!canEdit" @click="openEditMaterial(material)">Chỉnh sửa</button>
            <button type="button" class="rounded-lg p-2 text-muted hover:bg-primary/10 hover:text-primary disabled:opacity-50" :disabled="!canEdit" :aria-label="`Xóa tài liệu ${material.title}`" @click="removeMaterial(material)"><Trash2 :size="15" aria-hidden="true" /></button>
          </div>
        </div>
        <div v-if="material.fileUrl" class="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-background">
          <img v-if="fileKind(material) === 'image'" :src="material.fileUrl" :alt="material.title" class="mx-auto max-h-[480px] max-w-full object-contain">
          <iframe v-else-if="fileKind(material) === 'pdf'" :src="material.fileUrl" :title="`Xem trước ${material.title}`" class="h-[min(70vh,600px)] w-full border-0"></iframe>
          <video v-else-if="fileKind(material) === 'video'" :src="material.fileUrl" controls class="max-h-[480px] w-full bg-navy"></video>
          <div v-else class="p-4 text-sm text-muted">Định dạng này không xem trước được trong giao diện.</div>
          <a :href="material.fileUrl" :download="material.fileName || material.title" target="_blank" rel="noopener noreferrer" class="m-3 inline-flex text-xs font-semibold text-primary hover:underline">{{ fileKind(material) === 'download' ? 'Tải / mở tệp' : 'Mở tệp trong tab mới' }}</a>
        </div>
        <p v-else class="mt-4 rounded-lg border border-dashed border-slate-200 p-3 text-xs text-muted">Chưa có tệp thực tế để xem trước hoặc tải xuống.</p>
      </article>
      <p v-if="!course.materials.length" class="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">Chưa có tài liệu. Thêm tài liệu thật để xem trước hoặc tải xuống.</p>
    </section>

    <section v-if="assetType === 'material' && materialFormOpen" class="rounded-2xl border border-primary/20 bg-white p-5 shadow-sm">
      <h3 class="font-bold text-navy">{{ editingMaterialId ? 'Cập nhật tài liệu' : 'Thêm tài liệu' }}</h3>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <label class="text-xs font-semibold text-muted">Tên tài liệu *
          <input v-model="materialForm.title" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary">
        </label>
        <label class="text-xs font-semibold text-muted">Loại tài liệu
          <input v-model="materialForm.documentType" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary" placeholder="E-book, slide, bài tập...">
        </label>
        <label class="text-xs font-semibold text-muted md:col-span-2">Mô tả
          <textarea v-model="materialForm.description" rows="2" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary"></textarea>
        </label>
        <label class="text-xs font-semibold text-muted">Bài học liên quan
          <select v-model="materialForm.lessonId" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal text-navy">
            <option value="">Tài liệu toàn khóa học</option>
            <option v-for="lesson in lessons" :key="lesson.id" :value="lesson.id">{{ lesson.title || 'Bài học chưa đặt tên' }}</option>
          </select>
        </label>
        <label class="text-xs font-semibold text-muted">Chọn tệp thật
          <input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg" class="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" @change="setMaterialFile">
          <span class="mt-1 block font-normal">{{ materialForm.fileName || 'Chưa chọn tệp' }}</span>
        </label>
        <label class="text-xs font-semibold text-muted md:col-span-2">URL tệp đã có
          <input v-model="materialForm.fileUrl" type="url" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary" placeholder="Không tạo URL nếu chưa có tệp thật">
        </label>
      </div>
      <div class="mt-4 flex justify-end gap-2">
        <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-navy" @click="materialFormOpen = false">Hủy</button>
        <button type="button" class="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90" @click="saveMaterial">Lưu tài liệu</button>
      </div>
    </section>
    <p v-if="assetType === 'material'" class="text-xs leading-5 text-muted">PDF, hình ảnh và video có thể xem trước khi MIME type phù hợp. Tệp Office không được giả lập nội dung xem trước; chỉ có thể mở hoặc tải nếu URL tệp tồn tại.</p>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
