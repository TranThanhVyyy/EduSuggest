<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, FileVideo, Plus, Save, Trash2 } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  createProviderLesson,
  deleteProviderLesson,
  loadProviderCourse,
  providerErrorMessage,
  updateProviderLesson,
} from '@/service/providerApiService'

const route = useRoute()
const courseId = String(route.params.id)
const course = ref(null)
const loadError = ref('')
const errorMessage = ref('')
const toastMessage = ref('')

async function refresh() {
  try {
    course.value = await loadProviderCourse(courseId)
  } catch (error) {
    loadError.value = providerErrorMessage(error, 'Không thể tải danh sách bài học.')
  }
}

onMounted(refresh)

const lessons = computed(() => course.value?.lessons || [])
const canEdit = computed(() => course.value && [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(course.value.status))

async function run(action, successMessage) {
  try {
    await action()
    await refresh()
    errorMessage.value = ''
    toastMessage.value = successMessage
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể cập nhật bài học.')
  }
}

function addLesson() {
  lessons.value.push({
    id: `TEMP-${Date.now()}`,
    title: '',
    description: '',
    duration: '',
    durationMinutes: null,
    content: '',
    video: null,
    thuTu: lessons.value.length + 1,
  })
}

async function saveLesson(lesson) {
  if (!lesson.title.trim()) {
    errorMessage.value = 'Nhập tên bài học trước khi lưu.'
    return
  }
  const action = lesson.id.startsWith('TEMP-')
    ? () => createProviderLesson(courseId, lesson, lesson.thuTu)
    : () => updateProviderLesson(courseId, lesson.id, lesson)
  await run(action, 'Đã lưu bài học trên Backend.')
}

async function removeLesson(lesson) {
  if (lesson.id.startsWith('TEMP-')) {
    course.value.lessons = lessons.value.filter((item) => item.id !== lesson.id)
    return
  }
  await run(() => deleteProviderLesson(courseId, lesson.id), 'Đã xóa bài học trên Backend.')
}

async function shiftLesson(lesson, direction) {
  const index = lessons.value.findIndex((item) => item.id === lesson.id)
  const other = lessons.value[index + direction]
  if (!other || lesson.id.startsWith('TEMP-') || other.id.startsWith('TEMP-')) return

  await run(async () => {
    const lessonOrder = lesson.thuTu || index + 1
    const otherOrder = other.thuTu || index + 2
    await updateProviderLesson(courseId, lesson.id, { ...lesson, thuTu: otherOrder })
    await updateProviderLesson(courseId, other.id, { ...other, thuTu: lessonOrder })
  }, 'Đã cập nhật thứ tự bài học trên Backend.')
}
</script>

<template>
  <div v-if="loadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không thể mở quản lý bài học</h2>
    <p class="mt-2 text-sm text-muted">{{ loadError }}</p>
    <RouterLink :to="{ name: 'provider-courses' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink>
  </div>
  <div v-else-if="course" class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Quản lý nội dung · {{ course.id }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Bài học</h2>
        <p class="mt-2 text-sm text-muted">{{ course.title }} · {{ lessons.length }} bài học</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><ArrowLeft :size="15" aria-hidden="true" /> Chi tiết khóa học</RouterLink>
        <button type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="!canEdit" @click="addLesson"><Plus :size="16" aria-hidden="true" /> Thêm bài học</button>
      </div>
    </section>

    <p v-if="!canEdit" class="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-muted">Khóa học đang ở trạng thái {{ course.status }}. Bài học không thể thay đổi trong trạng thái này.</p>
    <p v-if="errorMessage" class="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>

    <section v-if="lessons.length" class="space-y-4">
      <article v-for="(lesson, index) in lessons" :key="lesson.id" class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <p class="text-sm font-bold text-navy">Bài học {{ index + 1 }}</p>
          <div class="flex gap-1">
            <button type="button" class="rounded-lg border border-slate-200 px-2 py-1 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || index === 0 || lesson.id.startsWith('TEMP-')" aria-label="Chuyển bài học lên" @click="shiftLesson(lesson, -1)">↑</button>
            <button type="button" class="rounded-lg border border-slate-200 px-2 py-1 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || index === lessons.length - 1 || lesson.id.startsWith('TEMP-')" aria-label="Chuyển bài học xuống" @click="shiftLesson(lesson, 1)">↓</button>
            <button type="button" class="rounded-lg border border-slate-200 p-1.5 text-muted disabled:opacity-40" :disabled="!canEdit" aria-label="Lưu bài học" @click="saveLesson(lesson)"><Save :size="14" aria-hidden="true" /></button>
            <button type="button" class="rounded-lg p-1.5 text-muted hover:text-primary disabled:opacity-40" :disabled="!canEdit" aria-label="Xóa bài học" @click="removeLesson(lesson)"><Trash2 :size="14" aria-hidden="true" /></button>
          </div>
        </div>
        <div class="mt-3 grid gap-3 md:grid-cols-2">
          <label class="text-xs font-semibold text-muted">Tên bài học
            <input v-model="lesson.title" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background">
          </label>
          <label class="text-xs font-semibold text-muted">Thời lượng (phút)
            <input v-model.number="lesson.durationMinutes" type="number" min="0" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background" placeholder="Ví dụ: 30">
          </label>
          <label class="text-xs font-semibold text-muted md:col-span-2">Nội dung văn bản
            <textarea v-model="lesson.content" :disabled="!canEdit" rows="4" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal leading-6 text-navy outline-none focus:border-primary disabled:bg-background"></textarea>
          </label>
        </div>
        <RouterLink :to="{ name: 'provider-videos', params: { id: course.id } }" class="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"><FileVideo :size="14" aria-hidden="true" /> Quản lý video và tài liệu</RouterLink>
      </article>
    </section>
    <p v-else class="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">Khóa học chưa có bài học.</p>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
