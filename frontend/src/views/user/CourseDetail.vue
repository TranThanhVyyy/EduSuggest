<script setup>
import { computed, ref } from 'vue'
import { ArrowLeft, BookOpen, CheckCircle2, Clock3, GraduationCap, LockKeyhole, Play } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import CourseCard from '@/components/user/CourseCard.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  enrollInCourse,
  getCourseProgress,
  getPublicCourse,
  getPublicCourses,
  isEnrolled,
} from '@/service/userService'

const route = useRoute()
const router = useRouter()
const course = computed(() => getPublicCourse(String(route.params.id)))
const enrolled = computed(() => course.value ? isEnrolled(course.value.id) : false)
const progress = computed(() => course.value ? getCourseProgress(course.value.id) : null)
const enrollmentConfirmOpen = ref(false)
const errorMessage = ref('')
const toastMessage = ref('')
const relatedCourses = computed(() => getPublicCourses().filter((item) => item.category === course.value?.category && item.id !== course.value?.id).slice(0, 2))
const lessons = computed(() => course.value?.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => ({ ...lesson, chapterTitle: chapter.title }))) || [])

function enroll() {
  try {
    const result = enrollInCourse(course.value.id)
    enrollmentConfirmOpen.value = false
    if (result.status === 'payment_required') {
      errorMessage.value = 'Khóa học này có phí. Thanh toán chưa được tích hợp nên chưa thể đăng ký hoặc xác nhận giao dịch.'
      return
    }
    if (result.status === 'already_enrolled') {
      router.push({ name: 'learning', params: { courseId: course.value.id } })
      return
    }
    errorMessage.value = ''
    toastMessage.value = 'Đã tạo đăng ký mẫu trong phiên trình duyệt; chưa gửi yêu cầu đến Backend.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể đăng ký khóa học.'
  }
}
</script>

<template>
  <div v-if="!course" class="rounded-2xl border border-slate-200 bg-white p-8 text-center"><h1 class="text-xl font-bold text-navy">Không tìm thấy khóa học</h1><p class="mt-2 text-sm text-muted">Khóa học không tồn tại hoặc chưa được phép hiển thị công khai.</p><RouterLink :to="{ name: 'course-catalog' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink></div>
  <div v-else class="space-y-6">
    <RouterLink :to="{ name: 'course-catalog' }" class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Danh sách khóa học</RouterLink>
    <section class="grid gap-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
      <div>
        <div class="flex flex-wrap gap-2 text-xs"><span class="rounded-full bg-primary/10 px-2.5 py-1 font-semibold text-primary">{{ course.category }}</span><span class="rounded-full bg-background px-2.5 py-1 text-muted">{{ course.level }}</span></div>
        <h1 class="mt-3 text-3xl font-bold tracking-tight text-navy">{{ course.title }}</h1>
        <p class="mt-3 max-w-3xl text-sm leading-6 text-muted">{{ course.description }}</p>
        <div class="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted"><span class="inline-flex items-center gap-2"><GraduationCap :size="16" aria-hidden="true" />{{ course.provider }}</span><span class="inline-flex items-center gap-2"><Clock3 :size="16" aria-hidden="true" />{{ course.duration }}</span><span class="inline-flex items-center gap-2"><BookOpen :size="16" aria-hidden="true" />{{ lessons.length }} bài học</span></div>
      </div>
      <aside class="h-fit rounded-xl border border-slate-200 bg-background p-5">
        <p class="text-2xl font-bold text-navy">{{ course.price > 0 ? new Intl.NumberFormat('vi-VN').format(course.price) + ' ₫' : 'Miễn phí' }}</p>
        <p class="mt-1 text-xs text-muted">Thông tin giá thuộc bộ dữ liệu minh họa.</p>
        <RouterLink v-if="enrolled" :to="{ name: 'learning', params: { courseId: course.id } }" class="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white hover:opacity-90"><Play :size="16" aria-hidden="true" /> Tiếp tục học</RouterLink>
        <button v-else type="button" class="mt-4 w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="course.price > 0" @click="enrollmentConfirmOpen = true">{{ course.price > 0 ? 'Thanh toán chưa tích hợp' : 'Đăng ký khóa học' }}</button>
        <p v-if="course.price > 0" class="mt-2 text-xs leading-5 text-muted">Không thể đăng ký khóa học có phí cho đến khi Backend cung cấp quy trình thanh toán.</p>
        <div v-if="enrolled && progress" class="mt-4"><div class="mb-1 flex justify-between text-xs text-muted"><span>Tiến độ mẫu</span><span>{{ progress.percentage }}%</span></div><div class="h-2 overflow-hidden rounded-full bg-white"><div class="h-full rounded-full bg-accent" :style="{ width: `${progress.percentage}%` }"></div></div></div>
      </aside>
    </section>

    <section class="grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(260px,0.75fr)]">
      <div class="space-y-5">
        <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><h2 class="text-lg font-bold text-navy">Bạn sẽ học được gì</h2><ul class="mt-4 grid gap-3 sm:grid-cols-2"><li v-for="objective in course.objectives" :key="objective" class="flex gap-2 text-sm text-muted"><CheckCircle2 :size="17" class="shrink-0 text-accent" aria-hidden="true" />{{ objective }}</li></ul></article>
        <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><h2 class="text-lg font-bold text-navy">Chương trình khóa học</h2><div class="mt-4 space-y-3"><details v-for="(chapter, index) in course.chapters" :key="chapter.id" class="rounded-xl border border-slate-200 p-4" :open="index === 0"><summary class="cursor-pointer font-semibold text-navy">{{ index + 1 }}. {{ chapter.title }} <span class="text-xs font-normal text-muted">· {{ chapter.lessons.length }} bài</span></summary><ul class="mt-3 divide-y divide-slate-100"><li v-for="lesson in chapter.lessons" :key="lesson.id" class="flex items-center justify-between gap-2 py-3 text-sm"><span class="flex items-center gap-2 text-navy"><component :is="enrolled ? Play : LockKeyhole" :size="15" class="text-muted" aria-hidden="true" />{{ lesson.title }}</span><span class="shrink-0 text-xs text-muted">{{ lesson.duration }}</span></li></ul></details></div><p v-if="!enrolled" class="mt-4 rounded-lg bg-background p-3 text-xs leading-5 text-muted">Nội dung bài học được giới hạn cho người đã đăng ký. Không hiển thị nội dung đầy đủ trước khi có quyền truy cập.</p></article>
      </div>
      <aside class="space-y-4">
        <article class="rounded-2xl border border-slate-200 bg-white p-5"><h2 class="font-bold text-navy">Thông tin khóa học</h2><dl class="mt-4 space-y-3 text-sm"><div><dt class="text-xs text-muted">Đối tượng phù hợp</dt><dd class="mt-1 text-navy">{{ course.audience }}</dd></div><div><dt class="text-xs text-muted">Kiến thức yêu cầu</dt><dd class="mt-1 text-navy">{{ course.prerequisites }}</dd></div><div><dt class="text-xs text-muted">Kết quả đạt được</dt><dd class="mt-1 text-navy">{{ course.outcomes }}</dd></div><div><dt class="text-xs text-muted">Đánh giá</dt><dd class="mt-1 text-muted">{{ course.rating == null ? 'Chưa có dữ liệu đánh giá' : `${course.rating} / 5` }}</dd></div></dl></article>
        <article class="rounded-2xl border border-slate-200 bg-white p-5"><h2 class="font-bold text-navy">Người cung cấp</h2><p class="mt-2 text-sm text-muted">{{ course.provider }}</p><p class="mt-1 text-xs text-muted">Thông tin liên hệ chưa được cung cấp.</p></article>
      </aside>
    </section>

    <section v-if="relatedCourses.length"><h2 class="mb-4 text-xl font-bold text-navy">Khóa học liên quan</h2><div class="grid gap-4 md:grid-cols-2"><CourseCard v-for="item in relatedCourses" :key="item.id" :course="item" /></div></section>

    <p v-if="errorMessage" class="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
    <AdminModal :open="enrollmentConfirmOpen" mode="confirm" title="Xác nhận đăng ký" :description="course.title" confirm-label="Xác nhận" @close="enrollmentConfirmOpen = false" @confirm="enroll"><p>Đăng ký miễn phí trong dữ liệu demo của phiên hiện tại. Chưa tạo quyền học trên Backend.</p></AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
