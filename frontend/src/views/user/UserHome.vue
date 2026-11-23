<script setup>
import { onMounted, ref } from 'vue'
import { ArrowRight, RefreshCw, Search } from 'lucide-vue-next'
import CourseCard from '@/components/user/CourseCard.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { fetchRecommendedCourses, fetchUserCourses } from '@/service/userApiService'

const courses = ref([])
const loading = ref(true)
const errorMessage = ref('')
const recommendation = ref({ items: [], strategy: 'none', personalized: false })
const recommendationLoading = ref(true)
const recommendationError = ref('')

async function loadCourses() {
  try { courses.value = (await fetchUserCourses()).slice(0, 3) }
  catch (error) { errorMessage.value = error.response?.data?.detail || 'Không thể tải danh mục khóa học.' }
  finally { loading.value = false }
}

async function loadRecommendations() {
  recommendationLoading.value = true
  recommendationError.value = ''
  try { recommendation.value = await fetchRecommendedCourses({ limit: 3 }) }
  catch (error) { recommendationError.value = error.response?.data?.detail || 'Không thể tải gợi ý khóa học.' }
  finally { recommendationLoading.value = false }
}

onMounted(() => { loadCourses(); loadRecommendations() })
</script>

<template>
  <div class="space-y-12">
    <section class="grid gap-8 border-b border-border pb-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)] lg:items-center lg:gap-16 lg:pb-14">
      <div>
        <p class="ui-eyebrow">EduSuggest · học tập theo mục tiêu</p>
        <h1 class="mt-4 max-w-2xl text-4xl font-medium leading-tight text-navy sm:text-5xl">Tìm khóa học cho bước tiếp theo của bạn</h1>
        <p class="mt-4 max-w-xl text-base leading-7 text-muted">Khám phá khóa học và tài liệu học tập; theo dõi tiến độ khi bạn bắt đầu.</p>
        <RouterLink :to="{ name: 'course-catalog' }" class="ui-button ui-button--primary mt-6"><Search :size="16" aria-hidden="true" /> Khám phá khóa học</RouterLink>
      </div>
      <div class="border-l-2 border-brand-accent pl-5 sm:pl-7">
        <p class="text-sm font-medium text-secondary">Bắt đầu tại đây</p>
        <h2 class="mt-2 text-2xl font-medium leading-snug text-navy">Một danh mục rõ ràng giúp bạn chọn nội dung phù hợp.</h2>
        <p class="mt-3 text-sm leading-6 text-muted">Danh mục chỉ hiển thị khóa học đã được phê duyệt và công khai.</p>
        <RouterLink :to="{ name: 'course-catalog' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Mở danh mục <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      </div>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-sm text-muted">Khám phá</p><h2 class="mt-1 text-xl font-semibold text-navy">Khóa học công khai</h2></div><RouterLink :to="{ name: 'course-catalog' }" class="text-sm font-medium text-secondary hover:underline">Tất cả khóa học</RouterLink></div>
      <div v-if="courses.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CourseCard v-for="course in courses" :key="course.id" :course="course" /></div>
      <p v-else-if="loading" class="border-y border-border py-6 text-sm text-muted" role="status">Đang tải khóa học…</p>
      <p v-else-if="errorMessage" class="border-y border-border py-6 text-sm text-danger" role="alert">{{ errorMessage }}</p>
      <p v-else class="border-y border-border py-6 text-sm text-muted">Chưa có khóa học công khai.</p>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-sm text-muted">Gợi ý</p><h2 class="mt-1 text-xl font-semibold text-navy">Khóa học dành cho bạn</h2></div><RouterLink :to="{ name: 'course-recommendations' }" class="text-sm font-medium text-secondary hover:underline">Xem tất cả gợi ý</RouterLink></div>
      <p v-if="recommendationLoading" class="border-y border-border py-5 text-sm text-muted" role="status">Đang tải gợi ý…</p>
      <div v-else-if="recommendationError" class="border-y border-border py-5" role="alert"><p class="text-sm text-danger">{{ recommendationError }}</p></div>
      <div v-else-if="recommendation.items.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <CourseCard v-for="item in recommendation.items" :key="item.id" :course="item" />
      </div>
      <div v-else class="border-y border-border py-5">
        <EmptyState title="Chưa có gợi ý khóa học" description="Backend hiện chưa có khóa học phù hợp để gợi ý." />
        <RouterLink :to="{ name: 'course-catalog' }" class="text-sm font-medium text-secondary hover:underline">Khám phá danh mục khóa học</RouterLink>
      </div>
    </section>

    <section>
      <div class="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p class="text-sm text-muted">Tài liệu</p><h2 class="mt-1 text-xl font-semibold text-navy">Tài liệu học tập</h2></div><RouterLink :to="{ name: 'material-catalog' }" class="text-sm font-medium text-secondary hover:underline">Tất cả tài liệu</RouterLink></div>
      <p class="border-y border-border py-5 text-sm text-muted">Danh mục tài liệu chưa có API cho người học.</p>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
      <div class="flex flex-wrap items-center justify-between gap-4"><div><h2 class="text-xl font-bold text-navy">Theo dõi tiến độ học tập</h2><p class="mt-2 text-sm text-muted">Tiếp tục các khóa học đã đăng ký và xem lại hoạt động.</p></div><RouterLink :to="{ name: 'learning-progress' }" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">Khóa học của tôi</RouterLink></div>
    </section>
  </div>
</template>
