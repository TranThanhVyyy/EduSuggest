<script setup>
import { computed, ref } from 'vue'
import { ArrowLeft, FileVideo, Plus, Save, Trash2 } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import {
  PROVIDER_STATUS,
  addProviderChapter,
  addProviderLesson,
  deleteProviderChapter,
  deleteProviderLesson,
  getProviderCourse,
  moveProviderChapter,
  moveProviderLesson,
  saveProviderChapter,
  saveProviderLesson,
} from '@/service/providerService'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'

const route = useRoute()
const courseId = String(route.params.id)
const course = ref(null)
const loadError = ref('')
const errorMessage = ref('')
const toastMessage = ref('')

function refresh() {
  try {
    course.value = JSON.parse(JSON.stringify(getProviderCourse(courseId)))
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Không thể tải cấu trúc khóa học.'
  }
}

refresh()

const canEdit = computed(() => course.value && [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(course.value.status))
const totalLessons = computed(() => course.value?.chapters.reduce((sum, chapter) => sum + chapter.lessons.length, 0) || 0)

function run(action, successMessage) {
  try {
    action()
    refresh()
    errorMessage.value = ''
    toastMessage.value = successMessage
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể cập nhật cấu trúc khóa học.'
  }
}

function addChapter() {
  run(() => addProviderChapter(courseId), 'Đã thêm chương trong phiên.')
}

function saveChapter(chapter) {
  run(() => saveProviderChapter(courseId, chapter.id, chapter), 'Đã lưu chương trong phiên.')
}

function removeChapter(chapter) {
  run(() => deleteProviderChapter(courseId, chapter.id), 'Đã xóa chương trong phiên.')
}

function shiftChapter(chapter, direction) {
  run(() => moveProviderChapter(courseId, chapter.id, direction), 'Đã cập nhật thứ tự chương.')
}

function addLesson(chapter) {
  run(() => addProviderLesson(courseId, chapter.id), 'Đã thêm bài học trong phiên.')
}

function saveLesson(chapter, lesson) {
  run(() => saveProviderLesson(courseId, chapter.id, lesson.id, lesson), 'Đã lưu bài học trong phiên.')
}

function removeLesson(chapter, lesson) {
  run(() => deleteProviderLesson(courseId, chapter.id, lesson.id), 'Đã xóa bài học trong phiên.')
}

function shiftLesson(chapter, lesson, direction) {
  run(() => moveProviderLesson(courseId, chapter.id, lesson.id, direction), 'Đã cập nhật thứ tự bài học.')
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
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Chương và bài học</h2>
        <p class="mt-2 text-sm text-muted">{{ course.title }} · {{ course.chapters.length }} chương · {{ totalLessons }} bài học</p>
      </div>
      <div class="flex gap-2">
        <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-navy hover:bg-background"><ArrowLeft :size="15" aria-hidden="true" /> Chi tiết khóa học</RouterLink>
        <button type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="!canEdit" @click="addChapter"><Plus :size="16" aria-hidden="true" /> Thêm chương</button>
      </div>
    </section>

    <p v-if="!canEdit" class="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-muted">Khóa học đang ở trạng thái {{ course.status }}. Nội dung đã gửi kiểm duyệt hoặc đã được xử lý không thể thay đổi tại thời điểm này.</p>
    <p v-if="errorMessage" class="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>

    <section v-if="course.chapters.length" class="space-y-4">
      <article v-for="(chapter, chapterIndex) in course.chapters" :key="chapter.id" class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
        <div class="flex flex-wrap items-start gap-3">
          <div class="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
            <label class="text-xs font-semibold text-muted">Tên chương
              <input v-model="chapter.title" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background" placeholder="Tên chương">
            </label>
            <label class="text-xs font-semibold text-muted">Mô tả
              <input v-model="chapter.description" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-background" placeholder="Mô tả chương">
            </label>
          </div>
          <div class="flex shrink-0 gap-1">
            <button type="button" class="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || chapterIndex === 0" aria-label="Chuyển chương lên" @click="shiftChapter(chapter, -1)">↑</button>
            <button type="button" class="rounded-lg border border-slate-200 px-2.5 py-2 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || chapterIndex === course.chapters.length - 1" aria-label="Chuyển chương xuống" @click="shiftChapter(chapter, 1)">↓</button>
            <button type="button" class="rounded-lg border border-slate-200 p-2 text-muted hover:bg-background disabled:opacity-40" :disabled="!canEdit" :aria-label="`Lưu chương ${chapter.title}`" @click="saveChapter(chapter)"><Save :size="15" aria-hidden="true" /></button>
            <button type="button" class="rounded-lg p-2 text-muted hover:bg-primary/10 hover:text-primary disabled:opacity-40" :disabled="!canEdit" :aria-label="`Xóa chương ${chapter.title}`" @click="removeChapter(chapter)"><Trash2 :size="15" aria-hidden="true" /></button>
          </div>
        </div>

        <div class="mt-4 space-y-3">
          <article v-for="(lesson, lessonIndex) in chapter.lessons" :key="lesson.id" class="rounded-xl border border-slate-200 bg-background p-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-sm font-bold text-navy">Bài học {{ lessonIndex + 1 }}</p>
              <div class="flex gap-1">
                <button type="button" class="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || lessonIndex === 0" aria-label="Chuyển bài học lên" @click="shiftLesson(chapter, lesson, -1)">↑</button>
                <button type="button" class="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-navy disabled:opacity-40" :disabled="!canEdit || lessonIndex === chapter.lessons.length - 1" aria-label="Chuyển bài học xuống" @click="shiftLesson(chapter, lesson, 1)">↓</button>
                <button type="button" class="rounded-lg border border-slate-200 bg-white p-1.5 text-muted disabled:opacity-40" :disabled="!canEdit" aria-label="Lưu bài học" @click="saveLesson(chapter, lesson)"><Save :size="14" aria-hidden="true" /></button>
                <button type="button" class="rounded-lg p-1.5 text-muted hover:text-primary disabled:opacity-40" :disabled="!canEdit" aria-label="Xóa bài học" @click="removeLesson(chapter, lesson)"><Trash2 :size="14" aria-hidden="true" /></button>
              </div>
            </div>
            <div class="mt-3 grid gap-3 md:grid-cols-2">
              <label class="text-xs font-semibold text-muted">Tên bài học
                <input v-model="lesson.title" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-white/60">
              </label>
              <label class="text-xs font-semibold text-muted">Thời lượng
                <input v-model="lesson.duration" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-white/60" placeholder="Ví dụ: 30 phút">
              </label>
              <label class="text-xs font-semibold text-muted md:col-span-2">Mô tả
                <input v-model="lesson.description" :disabled="!canEdit" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-navy outline-none focus:border-primary disabled:bg-white/60">
              </label>
              <label class="text-xs font-semibold text-muted md:col-span-2">Nội dung văn bản
                <textarea v-model="lesson.content" :disabled="!canEdit" rows="4" class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal leading-6 text-navy outline-none focus:border-primary disabled:bg-white/60"></textarea>
              </label>
            </div>
            <RouterLink :to="{ name: 'provider-videos', params: { id: course.id } }" class="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"><FileVideo :size="14" aria-hidden="true" /> Quản lý video bài học</RouterLink>
          </article>
          <p v-if="!chapter.lessons.length" class="rounded-lg border border-dashed border-slate-300 p-4 text-center text-sm text-muted">Chương này chưa có bài học.</p>
        </div>
        <button type="button" class="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-primary hover:bg-background disabled:cursor-not-allowed disabled:opacity-50" :disabled="!canEdit" @click="addLesson(chapter)"><Plus :size="14" aria-hidden="true" /> Thêm bài học</button>
      </article>
    </section>
    <p v-else class="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">Chưa có chương. Thêm chương đầu tiên để tạo cấu trúc khóa học.</p>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
