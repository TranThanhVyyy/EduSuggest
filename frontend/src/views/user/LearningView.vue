<script setup>
import { ref, watch } from 'vue'
import { ArrowLeft, CheckCircle2, Circle, ExternalLink, FileText } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { completeLearningLesson, fetchLearningCourse, fetchLearningProgress } from '@/service/userApiService'

const route = useRoute()
const course = ref(null)
const progress = ref(null)
const loading = ref(false)
const error = ref('')
const actionError = ref('')
const savingLesson = ref(null)
let sequence = 0

async function loadCourse(courseId) {
  const current = ++sequence
  loading.value = true
  error.value = ''
  actionError.value = ''
  course.value = null
  savingLesson.value = null
  try {
    const [learning, currentProgress] = await Promise.all([
      fetchLearningCourse(courseId), fetchLearningProgress(courseId),
    ])
    if (current !== sequence) return
    course.value = learning
    progress.value = currentProgress
  } catch (cause) {
    if (current === sequence) error.value = cause.response?.data?.detail || 'Không thể tải nội dung học.'
  } finally { if (current === sequence) loading.value = false }
}

async function completeLesson(lesson) {
  if (lesson.completed || savingLesson.value) return
  const current = sequence
  const courseId = String(route.params.courseId)
  savingLesson.value = lesson.id
  actionError.value = ''
  try {
    const updatedProgress = await completeLearningLesson(courseId, lesson.id)
    if (current !== sequence) return
    progress.value = updatedProgress
    lesson.completed = true
  } catch (cause) {
    if (current === sequence) actionError.value = cause.response?.data?.detail || 'Không thể lưu tiến độ bài học.'
  } finally { if (current === sequence) savingLesson.value = null }
}

watch(() => route.params.courseId, loadCourse, { immediate: true })
</script>

<template>
  <main class="max-w-4xl space-y-5">
    <RouterLink :to="{ name: 'learning-progress' }" class="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Khóa học của tôi</RouterLink>
    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải nội dung học…</p>
    <section v-else-if="error" class="border-l-2 border-danger py-1 pl-4" role="alert"><h1 class="ui-page-title">Không thể mở khóa học</h1><p class="mt-2 text-sm text-danger">{{ error }}</p><button class="mt-3 text-sm text-secondary underline" @click="loadCourse(route.params.courseId)">Thử lại</button></section>
    <template v-else-if="course">
      <header class="border-b border-border pb-5"><p class="ui-eyebrow">{{ progress?.completedLessons || 0 }}/{{ progress?.totalLessons || 0 }} bài hoàn thành · {{ progress?.percentage || 0 }}%</p><h1 class="ui-page-title mt-2">{{ course.course.title }}</h1><div class="mt-3 h-2 overflow-hidden rounded-full bg-background"><div class="h-full bg-accent" :style="{ width: `${progress?.percentage || 0}%` }"></div></div></header>
      <p v-if="actionError" class="text-sm text-danger" role="alert">{{ actionError }}</p>
      <EmptyState v-if="!course.lessons.length" title="Khóa học chưa có bài học" description="Nhà cung cấp chưa thêm nội dung bài học cho khóa học này." />
      <ol v-else class="divide-y divide-border border-y border-border">
        <li v-for="(lesson, index) in course.lessons" :key="lesson.id" class="py-5">
          <div class="flex flex-wrap items-start justify-between gap-3"><div class="flex min-w-0 items-start gap-3"><CheckCircle2 v-if="lesson.completed" :size="18" class="mt-1 shrink-0 text-success" aria-label="Đã hoàn thành" /><Circle v-else :size="18" class="mt-1 shrink-0 text-muted" aria-hidden="true" /><div class="min-w-0"><h2 class="font-semibold text-navy">{{ index + 1 }}. {{ lesson.title }}</h2><p v-if="lesson.content" class="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{{ lesson.content }}</p><a v-if="lesson.videoUrl" :href="lesson.videoUrl" target="_blank" rel="noopener noreferrer" class="mt-2 inline-flex items-center gap-1 text-sm text-secondary">Mở video <ExternalLink :size="13" aria-hidden="true" /></a><ul v-if="lesson.materials.length" class="mt-3 space-y-2"><li v-for="material in lesson.materials" :key="material.id" class="text-sm"><a :href="material.url" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 text-secondary hover:underline"><FileText :size="15" aria-hidden="true" />{{ material.title }}<ExternalLink :size="13" aria-hidden="true" /></a></li></ul></div></div><button class="ui-button ui-button--secondary shrink-0" :disabled="lesson.completed || savingLesson === lesson.id" @click="completeLesson(lesson)">{{ lesson.completed ? 'Đã hoàn thành' : savingLesson === lesson.id ? 'Đang lưu…' : 'Đánh dấu hoàn thành' }}</button></div>
        </li>
      </ol>
    </template>
  </main>
</template>
