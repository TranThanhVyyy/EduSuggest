<script setup>
import { computed } from 'vue'
import { ArrowRight, BookOpen, Search, Sparkles } from 'lucide-vue-next'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import { getPublicCourses, getPublicMaterials, getRecommendedCourses } from '@/service/userService'

const courses = computed(() => getPublicCourses().slice(0, 3))
const recommended = computed(() => getRecommendedCourses().slice(0, 2))
const materials = computed(() => getPublicMaterials().slice(0, 2).map((material) => ({
  ...material,
  courseTitle: getPublicCourses().find((course) => course.id === material.courseId)?.title || 'Chưa có thông tin',
  lessonTitle: 'Bài học liên quan',
  sizeLabel: material.sizeBytes ? `${Math.round(material.sizeBytes / 1024)} KB` : 'Chưa có dữ liệu',
})))
</script>

<template>
  <div class="space-y-10">
    <section class="grid gap-5 lg:grid-cols-[1.45fr_0.75fr]">
      <div class="rounded-3xl bg-primary p-6 text-white sm:p-9">
        <span class="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold"><Sparkles :size="15" aria-hidden="true" /> EduSuggest · học tập theo mục tiêu</span>
        <h1 class="mt-5 max-w-2xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">Học đúng điều bạn cần, tiến xa hơn mỗi ngày.</h1>
        <p class="mt-4 max-w-xl text-sm leading-6 text-white/85 sm:text-base">Khám phá khóa học và tài liệu học tập phù hợp với hành trình của bạn.</p>
        <div class="mt-7 flex flex-wrap gap-2">
          <RouterLink :to="{ name: 'course-catalog' }" class="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-primary hover:opacity-90"><Search :size="16" aria-hidden="true" /> Khám phá khóa học</RouterLink>
          <RouterLink :to="{ name: 'register' }" class="rounded-xl border border-white/35 px-4 py-3 text-sm font-semibold text-white hover:bg-white/10">Tạo tài khoản</RouterLink>
        </div>
      </div>
      <div class="flex flex-col justify-between rounded-2xl border border-accent/20 bg-accent/5 p-6 sm:p-8">
        <div><span class="flex size-11 items-center justify-center rounded-xl bg-accent/10 text-accent"><Sparkles :size="21" aria-hidden="true" /></span><p class="mt-4 text-sm font-semibold text-accent">Gợi ý dành cho bạn</p><h2 class="mt-1 text-xl font-bold text-navy">Khám phá nội dung mới</h2><p class="mt-2 text-sm leading-6 text-muted">Gợi ý mẫu được phân biệt rõ với kết quả của AI thật.</p></div>
        <RouterLink :to="{ name: 'course-recommendations' }" class="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">Xem gợi ý <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      </div>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-xs font-semibold uppercase tracking-wide text-muted">Được phê duyệt và công khai</p><h2 class="mt-1 text-xl font-bold text-navy">Khóa học nổi bật</h2></div><RouterLink :to="{ name: 'course-catalog' }" class="text-sm font-semibold text-primary hover:underline">Tất cả khóa học</RouterLink></div>
      <div v-if="courses.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CourseCard v-for="course in courses" :key="course.id" :course="course" /></div>
      <p v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-muted">Chưa có khóa học công khai.</p>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-xs font-semibold uppercase tracking-wide text-accent">Gợi ý mẫu</p><h2 class="mt-1 text-xl font-bold text-navy">Có thể bạn quan tâm</h2></div><RouterLink :to="{ name: 'course-recommendations' }" class="text-sm font-semibold text-primary hover:underline">Xem gợi ý</RouterLink></div>
      <div v-if="recommended.length" class="grid gap-4 md:grid-cols-2"><CourseCard v-for="course in recommended" :key="course.id" :course="course" /></div>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-xs font-semibold uppercase tracking-wide text-accent">Tài liệu</p><h2 class="mt-1 text-xl font-bold text-navy">Tài liệu học tập</h2></div><RouterLink :to="{ name: 'material-catalog' }" class="text-sm font-semibold text-primary hover:underline">Tất cả tài liệu</RouterLink></div>
      <div v-if="materials.length" class="grid gap-4 md:grid-cols-2"><MaterialCard v-for="material in materials" :key="material.id" :material="material" /></div>
      <p v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-muted">Chưa có tài liệu được phép truy cập.</p>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
      <div class="flex flex-wrap items-center justify-between gap-4"><div><h2 class="text-xl font-bold text-navy">Theo dõi tiến độ học tập</h2><p class="mt-2 text-sm text-muted">Tiếp tục các khóa học đã đăng ký và xem lại hoạt động.</p></div><RouterLink :to="{ name: 'learning-progress' }" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">Khóa học của tôi</RouterLink></div>
    </section>
  </div>
</template>
