<script setup>
import { onMounted, ref } from 'vue'
import { BookOpen, CheckCircle2, Clock3 } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { fetchMyEnrollments } from '@/service/userApiService'

const courses = ref([])
const loading = ref(true)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try { courses.value = await fetchMyEnrollments() }
  catch (cause) { error.value = cause.response?.data?.detail || 'Không thể tải danh sách khóa học.' }
  finally { loading.value = false }
}
function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="border-b border-border pb-5"><p class="ui-eyebrow">Học tập</p><h1 class="ui-page-title mt-2">Tiến độ học tập</h1><p class="mt-2 text-sm text-muted">Theo dõi các khóa học bạn đã đăng ký.</p></section>
    <p v-if="loading" class="py-5 text-sm text-muted" role="status">Đang tải khóa học…</p>
    <section v-else-if="error" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert"><p class="text-sm text-danger">{{ error }}</p><button class="mt-3 text-sm text-secondary underline" @click="load">Thử lại</button></section>
    <section v-else class="space-y-3">
      <article v-for="entry in courses" :key="entry.id" class="grid gap-4 rounded-xl border border-border bg-white p-4 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-center">
        <div class="flex min-w-0 items-start gap-3"><BookOpen :size="20" class="mt-1 shrink-0 text-primary" aria-hidden="true" /><div class="min-w-0"><RouterLink :to="{ name: 'course-detail', params: { id: entry.course.id } }" class="font-semibold text-navy hover:text-primary">{{ entry.course.title }}</RouterLink><p class="mt-1 text-xs text-muted">Bắt đầu {{ formatDate(entry.enrolledAt) }} · {{ entry.completedLessons }}/{{ entry.totalLessons }} bài</p><p v-if="entry.completedAt" class="mt-1 text-xs text-muted">Hoàn thành {{ formatDate(entry.completedAt) }}</p></div></div>
        <div><div class="mb-1.5 flex justify-between text-xs text-muted"><span class="inline-flex items-center gap-1"><CheckCircle2 v-if="entry.status === 'completed'" :size="14" class="text-success" aria-hidden="true" /><Clock3 v-else :size="14" aria-hidden="true" />{{ entry.status === 'completed' ? 'Hoàn thành' : 'Đang học' }}</span><span>{{ entry.progress }}%</span></div><div class="h-2 overflow-hidden rounded-full bg-background"><div class="h-full bg-accent" :style="{ width: `${entry.progress}%` }"></div></div><RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="mt-3 inline-flex text-xs font-semibold text-primary hover:underline">{{ entry.status === 'completed' ? 'Xem lại khóa học' : 'Tiếp tục học' }}</RouterLink></div>
      </article>
      <div v-if="!courses.length" class="max-w-2xl border-y border-border"><EmptyState title="Chưa đăng ký khóa học nào" description="Các khóa học bạn đăng ký sẽ xuất hiện tại đây." /></div>
    </section>
  </div>
</template>
