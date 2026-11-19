<script setup>
import { computed } from 'vue'
import { BookOpen, CheckCircle2, Clock3 } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { getCourseProgress, getLearningStats, getEnrolledCourses } from '@/service/userService'

const stats = computed(() => getLearningStats())
const courses = computed(() => getEnrolledCourses())

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
</script>

<template>
  <div class="space-y-5">
    <section><p class="text-sm text-muted">Học tập</p><h1 class="mt-1 text-2xl font-bold text-navy">Tiến độ học tập</h1><p class="mt-2 text-sm text-muted">Thống kê từ dữ liệu minh họa trong phiên hiện tại.</p></section>
    <section class="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Khóa đã đăng ký</p><p class="mt-2 text-2xl font-bold text-navy">{{ stats.totalCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Đang học</p><p class="mt-2 text-2xl font-bold text-primary">{{ stats.inProgressCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Đã hoàn thành</p><p class="mt-2 text-2xl font-bold text-accent">{{ stats.completedCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Bài học hoàn thành</p><p class="mt-2 text-2xl font-bold text-navy">{{ stats.completedLessons }}</p></article>
    </section>
    <section class="space-y-3">
      <article v-for="entry in courses" :key="entry.enrollment.id" class="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-center">
        <div class="flex min-w-0 items-start gap-3"><span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><BookOpen :size="19" aria-hidden="true" /></span><div class="min-w-0"><RouterLink :to="{ name: 'course-detail', params: { id: entry.course.id } }" class="font-bold text-navy hover:text-primary">{{ entry.course.title }}</RouterLink><p class="mt-1 text-xs text-muted">Bắt đầu {{ formatDate(entry.enrollment.enrolledAt) }} · {{ getCourseProgress(entry.course.id)?.completedLessons || 0 }}/{{ getCourseProgress(entry.course.id)?.totalLessons || 0 }} bài</p><p v-if="entry.enrollment.completedAt" class="mt-1 text-xs text-muted">Hoàn thành {{ formatDate(entry.enrollment.completedAt) }}</p></div></div>
        <div><div class="mb-1.5 flex justify-between text-xs text-muted"><span class="inline-flex items-center gap-1"><CheckCircle2 v-if="entry.enrollment.status === 'completed'" :size="14" class="text-accent" aria-hidden="true" /><Clock3 v-else :size="14" aria-hidden="true" />{{ entry.enrollment.status === 'completed' ? 'Hoàn thành' : 'Đang học' }}</span><span>{{ getCourseProgress(entry.course.id)?.percentage || 0 }}%</span></div><div class="h-2 overflow-hidden rounded-full bg-background"><div class="h-full rounded-full bg-accent" :style="{ width: `${getCourseProgress(entry.course.id)?.percentage || 0}%` }"></div></div><RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="mt-3 inline-flex text-xs font-semibold text-primary hover:underline">{{ entry.enrollment.status === 'completed' ? 'Xem lại khóa học' : 'Tiếp tục học' }}</RouterLink></div>
      </article>
      <div v-if="!courses.length" class="rounded-2xl border border-slate-200 bg-white"><EmptyState title="Chưa có khóa học" description="Các khóa học bạn đăng ký sẽ xuất hiện ở đây." /></div>
    </section>
  </div>
</template>
