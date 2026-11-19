<script setup>
import { computed } from 'vue'
import { ArrowRight, BookOpen, CheckCircle2, Clock3, Sparkles } from 'lucide-vue-next'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import {
  getCourseProgress,
  getEnrolledCourses,
  getLearningStats,
  getRecentLearningActivities,
  getRecommendedCourses,
  getRecommendedMaterials,
  getUserProfile,
} from '@/service/userService'

const profile = getUserProfile()
const stats = computed(() => getLearningStats())
const enrolled = computed(() => getEnrolledCourses().filter(({ enrollment }) => enrollment.status === 'in_progress').slice(0, 2))
const recommendedCourses = computed(() => getRecommendedCourses().slice(0, 2))
const recommendedMaterials = computed(() => getRecommendedMaterials().slice(0, 2).map((material) => enrichMaterial(material)))
const activities = computed(() => getRecentLearningActivities(5))

function enrichMaterial(material) {
  const course = getEnrolledCourses().find(({ course: item }) => item.id === material.courseId)?.course
  return {
    ...material,
    courseTitle: course?.title || 'Khóa học được đề xuất',
    lessonTitle: 'Bài học liên quan',
    sizeLabel: material.sizeBytes ? `${Math.round(material.sizeBytes / 1024)} KB` : 'Chưa có dữ liệu',
  }
}
</script>

<template>
  <div class="space-y-7">
    <section class="grid gap-5 lg:grid-cols-[1.4fr_0.8fr]">
      <div class="rounded-2xl bg-primary p-6 text-white sm:p-8">
        <p class="text-sm font-semibold text-white/75">Không gian học tập minh họa</p>
        <h1 class="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Xin chào, {{ profile.fullName.split(' ')[0] }}!</h1>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/85">Tiếp tục hành trình học tập của bạn và khám phá nội dung mới phù hợp với mục tiêu.</p>
        <div class="mt-6 flex flex-wrap gap-2">
          <RouterLink :to="{ name: 'course-catalog' }" class="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-primary hover:opacity-90">Khám phá khóa học</RouterLink>
          <RouterLink :to="{ name: 'course-recommendations' }" class="inline-flex items-center gap-2 rounded-xl border border-white/30 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/10"><Sparkles :size="16" aria-hidden="true" /> Gợi ý dành cho bạn</RouterLink>
        </div>
      </div>
      <div class="rounded-2xl border border-accent/20 bg-accent/5 p-6">
        <span class="flex size-11 items-center justify-center rounded-xl bg-accent/10 text-accent"><Sparkles :size="21" aria-hidden="true" /></span>
        <h2 class="mt-4 text-lg font-bold text-navy">Gợi ý học tập</h2>
        <p class="mt-2 text-sm leading-6 text-muted">Danh sách gợi ý đang dùng mẫu minh họa; chưa có kết quả từ hệ thống AI.</p>
        <RouterLink :to="{ name: 'course-recommendations' }" class="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">Xem gợi ý <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      </div>
    </section>

    <section class="grid grid-cols-2 gap-3 xl:grid-cols-4" aria-label="Thống kê học tập">
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Khóa đã đăng ký</p><p class="mt-2 text-2xl font-bold text-navy">{{ stats.totalCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Đang học</p><p class="mt-2 text-2xl font-bold text-primary">{{ stats.inProgressCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Đã hoàn thành</p><p class="mt-2 text-2xl font-bold text-accent">{{ stats.completedCourses }}</p></article>
      <article class="rounded-xl border border-slate-200 bg-white p-4"><p class="text-xs text-muted">Bài học hoàn thành</p><p class="mt-2 text-2xl font-bold text-navy">{{ stats.completedLessons }}</p></article>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div><p class="text-xs font-semibold uppercase tracking-wide text-muted">Tiếp tục hành trình</p><h2 class="mt-1 text-xl font-bold text-navy">Đang học</h2></div>
        <RouterLink :to="{ name: 'learning-progress' }" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">Tất cả khóa học của tôi <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      </div>
      <div v-if="enrolled.length" class="grid gap-4 lg:grid-cols-2">
        <article v-for="entry in enrolled" :key="entry.enrollment.id" class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0"><p class="text-xs font-semibold text-primary">{{ entry.course.category }} · {{ entry.course.duration }}</p><h3 class="mt-1 line-clamp-2 font-bold text-navy">{{ entry.course.title }}</h3><p class="mt-1 text-xs text-muted">Bài gần nhất: {{ entry.course.chapters.flatMap((chapter) => chapter.lessons).find((lesson) => lesson.id === entry.enrollment.currentLessonId)?.title || 'Chưa có dữ liệu' }}</p></div>
            <BookOpen class="shrink-0 text-muted" :size="19" aria-hidden="true" />
          </div>
          <div class="mt-4">
            <div class="mb-1.5 flex justify-between text-xs text-muted"><span>Tiến độ</span><span>{{ getCourseProgress(entry.course.id)?.percentage || 0 }}%</span></div>
            <div class="h-2 overflow-hidden rounded-full bg-background"><div class="h-full rounded-full bg-primary" :style="{ width: `${getCourseProgress(entry.course.id)?.percentage || 0}%` }"></div></div>
          </div>
          <RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:opacity-90"><Clock3 :size="14" aria-hidden="true" /> Tiếp tục học</RouterLink>
        </article>
      </div>
      <div v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-muted">Bạn chưa có khóa học đang học. <RouterLink :to="{ name: 'course-catalog' }" class="font-semibold text-primary hover:underline">Khám phá khóa học</RouterLink></div>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-xs font-semibold uppercase tracking-wide text-accent">Dữ liệu gợi ý mẫu</p><h2 class="mt-1 text-xl font-bold text-navy">Có thể bạn quan tâm</h2></div><RouterLink :to="{ name: 'course-recommendations' }" class="text-sm font-semibold text-primary hover:underline">Xem tất cả</RouterLink></div>
      <div v-if="recommendedCourses.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CourseCard v-for="course in recommendedCourses" :key="course.id" :course="course" /></div>
      <p v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-muted">Chưa có gợi ý khóa học.</p>
    </section>

    <section class="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
      <div>
        <div class="mb-4 flex items-end justify-between gap-2"><div><p class="text-xs font-semibold uppercase tracking-wide text-accent">Tài liệu gợi ý mẫu</p><h2 class="mt-1 text-xl font-bold text-navy">Tài liệu phù hợp</h2></div><RouterLink :to="{ name: 'material-recommendations' }" class="text-sm font-semibold text-primary hover:underline">Xem tất cả</RouterLink></div>
        <div v-if="recommendedMaterials.length" class="grid gap-3 sm:grid-cols-2"><MaterialCard v-for="material in recommendedMaterials" :key="material.id" :material="material" /></div>
        <p v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-muted">Chưa có gợi ý tài liệu.</p>
      </div>
      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <div class="flex items-center justify-between"><h2 class="font-bold text-navy">Hoạt động gần đây</h2><CheckCircle2 class="text-accent" :size="18" aria-hidden="true" /></div>
        <ul v-if="activities.length" class="mt-3 divide-y divide-slate-100">
          <li v-for="activity in activities" :key="activity.id" class="py-3"><p class="text-sm font-medium text-navy">{{ activity.title }}</p><p class="mt-1 text-xs text-muted">{{ new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(new Date(activity.createdAt)) }}</p></li>
        </ul>
        <p v-else class="mt-3 text-sm text-muted">Chưa có hoạt động.</p>
      </article>
    </section>
  </div>
</template>
