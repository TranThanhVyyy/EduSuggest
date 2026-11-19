<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, ChevronRight, FileText, LockKeyhole, Play } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getPublicMaterial, getLearningCourse, markLessonCompleted, setCurrentLesson } from '@/service/userService'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => String(route.params.courseId || ''))
const access = computed(() => getLearningCourse(courseId.value))
const lessons = computed(() => access.value?.course.chapters.flatMap((chapter, chapterIndex) =>
  chapter.lessons.map((lesson, lessonIndex) => ({ ...lesson, chapter, chapterIndex, lessonIndex })),
) || [])
const selectedLessonId = ref('')
const errorMessage = ref('')
const toastMessage = ref('')
const expandedChapters = ref(new Set())

watch(
  () => [courseId.value, route.query.lessonId, access.value?.enrollment.currentLessonId],
  ([, queryLessonId, storedLessonId]) => {
    const desiredId = typeof queryLessonId === 'string' ? queryLessonId : storedLessonId
    selectedLessonId.value = lessons.value.some((lesson) => lesson.id === desiredId)
      ? desiredId
      : lessons.value[0]?.id || ''
    expandedChapters.value = new Set(lessons.value.filter((lesson) => lesson.id === selectedLessonId.value).map((lesson) => lesson.chapter.id))
  },
  { immediate: true },
)

const currentIndex = computed(() => lessons.value.findIndex((lesson) => lesson.id === selectedLessonId.value))
const currentLesson = computed(() => currentIndex.value >= 0 ? lessons.value[currentIndex.value] : null)
const completed = computed(() => Boolean(currentLesson.value && access.value?.enrollment.completedLessonIds.includes(currentLesson.value.id)))
const attachedMaterials = computed(() => (currentLesson.value?.materialIds || []).map((id) => getPublicMaterial(id)).filter(Boolean))

function chooseLesson(lesson) {
  try {
    setCurrentLesson(courseId.value, lesson.id)
    selectedLessonId.value = lesson.id
    errorMessage.value = ''
    router.replace({ query: { lessonId: lesson.id } })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể mở bài học.'
  }
}

function moveLesson(direction) {
  const next = lessons.value[currentIndex.value + direction]
  if (next) chooseLesson(next)
}

function toggleChapter(chapterId) {
  const expanded = new Set(expandedChapters.value)
  if (expanded.has(chapterId)) expanded.delete(chapterId)
  else expanded.add(chapterId)
  expandedChapters.value = expanded
}

function markComplete() {
  try {
    markLessonCompleted(courseId.value, currentLesson.value.id)
    errorMessage.value = ''
    toastMessage.value = 'Đã cập nhật tiến độ mẫu trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể cập nhật tiến độ.'
  }
}

function formatBytes(bytes) {
  if (!bytes) return 'Dung lượng chưa có dữ liệu'
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div v-if="!access" class="rounded-2xl border border-slate-200 bg-white p-8 text-center">
    <LockKeyhole class="mx-auto text-muted" :size="24" aria-hidden="true" />
    <h1 class="mt-3 text-xl font-bold text-navy">Chưa có quyền truy cập khóa học</h1>
    <p class="mt-2 text-sm text-muted">Chỉ khóa học đã đăng ký mới mở được nội dung bài học.</p>
    <RouterLink :to="{ name: 'course-detail', params: { id: courseId } }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Xem khóa học</RouterLink>
  </div>
  <div v-else class="space-y-4">
    <section class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <div><RouterLink :to="{ name: 'learning-progress' }" class="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"><ArrowLeft :size="13" aria-hidden="true" /> Khóa học của tôi</RouterLink><h1 class="mt-1 text-lg font-bold text-navy">{{ access.course.title }}</h1></div>
      <p class="text-xs text-muted">{{ access.course.chapters.length }} chương · {{ lessons.length }} bài học</p>
    </section>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <main class="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
        <div v-if="currentLesson">
          <p class="text-xs font-semibold text-primary">{{ currentLesson.chapter.title }} · {{ currentLesson.duration }}</p>
          <h2 class="mt-2 text-2xl font-bold text-navy">{{ currentLesson.title }}</h2>
          <div v-if="currentLesson.type === 'video' && currentLesson.videoUrl" class="mt-5 overflow-hidden rounded-xl bg-navy"><video :src="currentLesson.videoUrl" controls class="max-h-[65vh] w-full"></video></div>
          <div v-else-if="currentLesson.type === 'video'" class="mt-5 flex min-h-44 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-background p-6 text-center">
            <p class="max-w-md text-sm leading-6 text-muted">Chưa có URL video thực tế cho bài học này. Không tạo trình phát giả.</p>
          </div>
          <article class="mt-5">
            <h3 class="font-bold text-navy">Nội dung bài học</h3>
            <p v-if="currentLesson.content" class="mt-2 whitespace-pre-line text-sm leading-7 text-navy">{{ currentLesson.content }}</p>
            <p v-else class="mt-2 text-sm text-muted">Chưa có nội dung văn bản.</p>
          </article>
          <section class="mt-5">
            <h3 class="font-bold text-navy">Tài liệu bài học</h3>
            <ul v-if="attachedMaterials.length" class="mt-2 space-y-2">
              <li v-for="material in attachedMaterials" :key="material.id" class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 p-3">
                <span class="flex items-center gap-2 text-sm font-medium text-navy"><FileText :size="16" class="text-muted" aria-hidden="true" />{{ material.title }} · {{ material.format }} · {{ formatBytes(material.sizeBytes) }}</span>
                <RouterLink :to="{ name: 'material-detail', params: { id: material.id } }" class="text-xs font-semibold text-primary hover:underline">Xem tài liệu</RouterLink>
              </li>
            </ul>
            <p v-else class="mt-2 text-sm text-muted">Bài học chưa có tài liệu được phép truy cập.</p>
          </section>
          <p v-if="errorMessage" class="mt-4 rounded-lg bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
          <div class="mt-6 flex flex-wrap justify-between gap-2 border-t border-slate-100 pt-4">
            <button type="button" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background disabled:opacity-40" :disabled="currentIndex <= 0" @click="moveLesson(-1)"><ArrowLeft :size="15" aria-hidden="true" /> Bài trước</button>
            <button v-if="!completed" type="button" class="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90" @click="markComplete"><CheckCircle2 :size="16" aria-hidden="true" /> Đánh dấu hoàn thành</button>
            <span v-else class="inline-flex items-center gap-1 text-sm font-semibold text-accent"><CheckCircle2 :size="16" aria-hidden="true" /> Đã hoàn thành</span>
            <button type="button" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40" :disabled="currentIndex >= lessons.length - 1" @click="moveLesson(1)">Bài tiếp <ArrowRight :size="15" aria-hidden="true" /></button>
          </div>
        </div>
        <p v-else class="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-muted">Khóa học chưa có bài học.</p>
      </main>

      <aside class="h-fit rounded-2xl border border-slate-200 bg-white p-4">
        <h2 class="font-bold text-navy">Nội dung khóa học</h2>
        <div class="mt-3 space-y-2">
          <section v-for="chapter in access.course.chapters" :key="chapter.id" class="overflow-hidden rounded-xl border border-slate-200">
            <button type="button" class="flex w-full items-center justify-between gap-2 bg-background px-3 py-3 text-left text-sm font-semibold text-navy" :aria-expanded="expandedChapters.has(chapter.id)" @click="toggleChapter(chapter.id)"><span>{{ chapter.title }}</span><ChevronDown v-if="expandedChapters.has(chapter.id)" :size="15" aria-hidden="true" /><ChevronRight v-else :size="15" aria-hidden="true" /></button>
            <ul v-if="expandedChapters.has(chapter.id)" class="divide-y divide-slate-100">
              <li v-for="lesson in chapter.lessons" :key="lesson.id">
                <button type="button" class="flex w-full items-start gap-2 px-3 py-3 text-left hover:bg-background" :class="selectedLessonId === lesson.id ? 'bg-primary/5' : ''" @click="chooseLesson(lesson)">
                  <CheckCircle2 v-if="access.enrollment.completedLessonIds.includes(lesson.id)" :size="15" class="mt-0.5 shrink-0 text-accent" aria-label="Đã hoàn thành" />
                  <Play v-else :size="15" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
                  <span class="min-w-0"><span class="block text-xs font-medium text-navy">{{ lesson.title }}</span><span class="mt-1 block text-[11px] text-muted">{{ lesson.duration }}</span></span>
                </button>
              </li>
            </ul>
          </section>
        </div>
      </aside>
    </div>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
