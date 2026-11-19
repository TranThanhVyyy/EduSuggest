<script setup>
import { computed } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import CourseCard from '@/components/user/CourseCard.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { useRoute } from 'vue-router'
import { getPublicCourses, getRecommendedCourses, getRecommendedMaterials } from '@/service/userService'

const route = useRoute()
const isMaterialView = computed(() => route.name === 'material-recommendations')
const title = computed(() => isMaterialView.value ? 'Tài liệu phù hợp với bạn' : 'Khóa học dành riêng cho bạn')
const courses = computed(() => getRecommendedCourses())
const materials = computed(() => getRecommendedMaterials().map((material) => ({
  ...material,
  courseTitle: getPublicCourses().find((course) => course.id === material.courseId)?.title || 'Chưa có thông tin',
  lessonTitle: 'Bài học liên quan',
  sizeLabel: material.sizeBytes ? `${Math.round(material.sizeBytes / 1024)} KB` : 'Chưa có dữ liệu',
})))
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-2xl border border-accent/20 bg-accent/5 p-5 sm:p-7">
      <span class="inline-flex items-center gap-2 text-sm font-semibold text-accent"><Sparkles :size="17" aria-hidden="true" /> Gợi ý học tập</span>
      <h1 class="mt-2 text-2xl font-bold text-navy">{{ title }}</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">Các thẻ hiện lấy từ Mock Data được đánh dấu; chưa gọi hệ thống AI. Không có điểm phù hợp hoặc lý do gợi ý nếu nguồn dữ liệu chưa cung cấp.</p>
    </section>
    <template v-if="isMaterialView">
      <div v-if="materials.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><MaterialCard v-for="material in materials" :key="material.id" :material="material" /></div>
      <div v-else class="rounded-2xl border border-slate-200 bg-white"><EmptyState title="Chưa có gợi ý tài liệu" description="Khi API gợi ý cung cấp kết quả, tài liệu phù hợp sẽ xuất hiện tại đây." /></div>
    </template>
    <template v-else>
      <div v-if="courses.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CourseCard v-for="course in courses" :key="course.id" :course="course" /></div>
      <div v-else class="rounded-2xl border border-slate-200 bg-white"><EmptyState title="Chưa có gợi ý khóa học" description="Khi API gợi ý cung cấp kết quả, khóa học phù hợp sẽ xuất hiện tại đây." /></div>
    </template>
    <p class="text-xs text-muted">{{ isMaterialView ? getRecommendedMaterials().length : getRecommendedCourses().length }} kết quả từ bộ dữ liệu minh họa.</p>
  </div>
</template>
