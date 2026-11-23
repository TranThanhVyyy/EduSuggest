<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, BookOpen, UserRound } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { authState } from '@/service/authState'
import CourseCard from '@/components/user/CourseCard.vue'
import { fetchMyEnrollments, fetchRecommendedCourses } from '@/service/userApiService'

const name = computed(() => authState.user?.hoTen?.trim() || 'Người học')
const enrolled = ref([])
const enrollmentsLoading = ref(true)
const enrollmentError = ref('')
const recommendation = ref({ items: [], strategy: 'none', personalized: false })
const recommendationLoading = ref(true)
const recommendationError = ref('')
async function loadEnrollments() {
  enrollmentsLoading.value = true
  enrollmentError.value = ''
  try { enrolled.value = await fetchMyEnrollments() }
  catch (error) { enrollmentError.value = error.response?.data?.detail || 'Không thể tải khóa học đã đăng ký.' }
  finally { enrollmentsLoading.value = false }
}
async function loadRecommendations() {
  recommendationLoading.value = true
  recommendationError.value = ''
  try { recommendation.value = await fetchRecommendedCourses({ limit: 6 }) }
  catch (error) { recommendationError.value = error.response?.data?.detail || 'Không thể tải gợi ý khóa học.' }
  finally { recommendationLoading.value = false }
}
onMounted(() => { loadEnrollments(); loadRecommendations() })
</script>

<template>
  <div class="space-y-10">
    <section class="grid gap-8 border-b border-border pb-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)] lg:items-end lg:pb-10">
      <div>
        <p class="ui-eyebrow">Không gian học tập</p>
        <h1 class="ui-page-title mt-3">{{ name }}</h1>
        <p class="mt-3 max-w-2xl text-base leading-7 text-muted">Các khóa học và hoạt động học tập của bạn sẽ được tổng hợp tại đây.</p>
        <RouterLink :to="{ name: 'course-catalog' }" class="ui-button ui-button--primary mt-6">Khám phá khóa học <ArrowRight :size="16" aria-hidden="true" /></RouterLink>
      </div>
      <nav class="grid gap-2 sm:grid-cols-2 lg:grid-cols-1" aria-label="Lối tắt học tập">
        <RouterLink :to="{ name: 'learning-progress' }" class="flex min-h-12 items-center justify-between gap-3 border-b border-border px-1 py-3 text-sm font-medium text-navy hover:text-secondary">
          <span class="inline-flex items-center gap-3"><BookOpen :size="17" class="text-muted" aria-hidden="true" /> Khóa học của tôi</span><ArrowRight :size="15" aria-hidden="true" />
        </RouterLink>
        <RouterLink :to="{ name: 'user-profile' }" class="flex min-h-12 items-center justify-between gap-3 border-b border-border px-1 py-3 text-sm font-medium text-navy hover:text-secondary">
          <span class="inline-flex items-center gap-3"><UserRound :size="17" class="text-muted" aria-hidden="true" /> Hồ sơ cá nhân</span><ArrowRight :size="15" aria-hidden="true" />
        </RouterLink>
      </nav>
    </section>

    <section aria-labelledby="enrolled-heading">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div><p class="text-sm text-muted">Tiến độ</p><h2 id="enrolled-heading" class="mt-1 text-xl font-semibold text-navy">Khóa học đang học</h2></div>
        <RouterLink :to="{ name: 'learning-progress' }" class="text-sm font-medium text-secondary hover:underline">Xem tiến độ <ArrowRight class="inline" :size="15" aria-hidden="true" /></RouterLink>
      </div>
      <p v-if="enrollmentsLoading" class="border-y border-border py-4 text-sm text-muted" role="status">Đang tải khóa học…</p>
      <div v-else-if="enrollmentError" class="border-y border-border py-4" role="alert"><p class="text-sm text-danger">{{ enrollmentError }}</p><button class="mt-2 text-sm text-secondary underline" @click="loadEnrollments">Thử lại</button></div>
      <div v-else-if="enrolled.length" class="divide-y divide-border border-y border-border">
        <article v-for="entry in enrolled" :key="entry.id" class="flex flex-wrap items-center justify-between gap-4 py-4">
          <div><h3 class="font-medium text-navy">{{ entry.course.title }}</h3><p class="mt-1 text-sm text-muted">{{ entry.progress }}% · {{ entry.completedLessons }}/{{ entry.totalLessons }} bài hoàn thành</p></div>
          <RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="text-sm font-medium text-secondary hover:underline">Tiếp tục học</RouterLink>
        </article>
      </div>
      <div v-else-if="!enrollmentsLoading && !enrollmentError" class="border-y border-border py-2">
        <EmptyState title="Chưa có khóa học đang học" description="Khi có khóa học và dữ liệu đăng ký, tiến độ sẽ hiển thị tại đây." />
      </div>
    </section>

    <section aria-labelledby="recommendations-heading" class="border-t border-border pt-6">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div><p class="text-sm text-muted">Cá nhân hóa</p><h2 id="recommendations-heading" class="mt-1 text-xl font-semibold text-navy">Khóa học dành cho bạn</h2></div>
        <RouterLink :to="{ name: 'course-recommendations' }" class="text-sm font-medium text-secondary hover:underline">Xem gợi ý <ArrowRight class="inline" :size="15" aria-hidden="true" /></RouterLink>
      </div>
      <p v-if="recommendationLoading" class="border-y border-border py-4 text-sm text-muted" role="status">Đang tải gợi ý khóa học…</p>
      <div v-else-if="recommendationError" class="border-y border-border py-4" role="alert"><p class="text-sm text-danger">{{ recommendationError }}</p><button class="mt-2 text-sm text-secondary underline" @click="loadRecommendations">Thử lại</button></div>
      <template v-else>
        <p v-if="recommendation.strategy === 'latest'" class="mb-4 text-sm text-muted" role="status">Chưa có đủ lịch sử học tập để cá nhân hóa. Các khóa học dưới đây là gợi ý khám phá mới cập nhật.</p>
        <div v-if="recommendation.personalized && recommendation.items.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <CourseCard v-for="item in recommendation.items" :key="item.id" :course="item" />
        </div>
        <div v-else-if="recommendation.items.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Khám phá khóa học">
          <CourseCard v-for="item in recommendation.items" :key="item.id" :course="item" />
        </div>
        <div v-else class="flex flex-wrap items-center justify-between gap-3 border-y border-border py-4">
          <p class="text-sm text-muted">Backend hiện chưa có khóa học phù hợp để gợi ý.</p>
          <RouterLink :to="{ name: 'course-catalog' }" class="text-sm font-medium text-secondary hover:underline">Khám phá danh mục khóa học <ArrowRight class="inline" :size="15" aria-hidden="true" /></RouterLink>
        </div>
      </template>
    </section>

    <section class="border-t border-border pt-6" aria-labelledby="explore-heading">
      <p class="text-sm text-muted">Khám phá</p>
      <h2 id="explore-heading" class="mt-1 text-lg font-semibold text-navy">Tìm thêm khóa học</h2>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-muted">Mở danh mục để tìm kiếm và lọc các khóa học công khai do Backend cung cấp.</p>
      <RouterLink :to="{ name: 'course-catalog' }" class="mt-3 inline-flex min-h-11 items-center gap-2 text-sm font-medium text-secondary hover:underline">Mở danh mục <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
    </section>
  </div>
</template>
