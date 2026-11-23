<script setup>
import { ref, watch } from 'vue'
import { ArrowLeft, ExternalLink, FileText, RefreshCw } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { enrollUserInCourse, fetchMyEnrollments, fetchUserCategories, fetchUserCourse, fetchSimilarCourses } from '@/service/userApiService'

const route = useRoute()
const course = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const categoryError = ref('')
const enrollment = ref(null)
const enrollmentLoading = ref(false)
const enrollmentError = ref('')
const enrollmentSuccess = ref('')
const similarCourses = ref([])
const similarLoading = ref(false)
const similarError = ref('')
let requestSequence = 0

async function loadCourse(id) {
  const sequence = ++requestSequence
  course.value = null
  errorMessage.value = ''
  categoryError.value = ''
  enrollmentError.value = ''
  enrollmentSuccess.value = ''
  enrollment.value = null
  enrollmentLoading.value = false
  loading.value = true
  similarCourses.value = []
  similarError.value = ''
  try {
    const courseData = await fetchUserCourse(id)
    if (sequence !== requestSequence) return
    course.value = courseData
    try {
      const enrollments = await fetchMyEnrollments()
      if (sequence !== requestSequence) return
      enrollment.value = enrollments.find((item) => item.course.id === String(id)) || null
    } catch (error) {
      if (sequence !== requestSequence) return
      enrollmentError.value = error.response?.data?.detail || 'Không thể kiểm tra trạng thái đăng ký.'
    }
    try {
      const categories = await fetchUserCategories()
      if (sequence !== requestSequence) return
      const categoryName = categories.find((category) => category.id === String(courseData.categoryId))?.name
      course.value = { ...courseData, category: categoryName || courseData.category }
    } catch (error) {
      if (sequence !== requestSequence) return
      categoryError.value = error.response?.data?.detail || 'Không thể tải tên danh mục; các thông tin khóa học vẫn được hiển thị.'
    }
    await loadSimilarCourses(id, sequence)
  } catch (error) {
    if (sequence !== requestSequence) return
    errorMessage.value = error.response?.data?.detail || 'Không thể tải khóa học. Hãy thử lại.'
  } finally { if (sequence === requestSequence) loading.value = false }
}

async function loadSimilarCourses(courseId, parentSequence) {
  similarLoading.value = true
  similarError.value = ''
  try {
    const result = await fetchSimilarCourses(courseId, { limit: 6 })
    if (parentSequence !== requestSequence) return
    similarCourses.value = result
  } catch (cause) {
    if (parentSequence !== requestSequence) return
    similarError.value = cause.response?.data?.detail || 'Không thể tải khóa học tương tự.'
  } finally {
    if (parentSequence === requestSequence) similarLoading.value = false
  }
}
async function enroll() {
  if (!course.value || enrollmentLoading.value || enrollment.value) return
  const current = requestSequence
  const courseId = course.value.id
  enrollmentLoading.value = true
  enrollmentError.value = ''
  enrollmentSuccess.value = ''
  try {
    const result = await enrollUserInCourse(courseId)
    if (current !== requestSequence) return
    enrollment.value = result
    enrollmentSuccess.value = 'Đăng ký khóa học thành công.'
    try {
      const refreshedCourse = await fetchUserCourse(courseId)
      if (current === requestSequence) course.value = refreshedCourse
    } catch {
      if (current === requestSequence) enrollmentError.value = 'Đăng ký đã thành công. Tải lại trang để mở nội dung khóa học.'
    }
  } catch (error) {
    if (current === requestSequence) enrollmentError.value = error.response?.data?.detail || 'Không thể đăng ký khóa học. Hãy thử lại.'
  } finally { if (current === requestSequence) enrollmentLoading.value = false }
}
watch(() => route.params.id, loadCourse, { immediate: true })
</script>

<template>
  <main class="max-w-4xl space-y-6">
    <RouterLink :to="{ name: 'course-catalog' }" class="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Danh sách khóa học</RouterLink>
    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải khóa học…</p>
    <section v-else-if="errorMessage" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert"><h1 class="ui-page-title">Không thể tải khóa học</h1><p class="mt-2 text-sm leading-6 text-danger">{{ errorMessage }}</p><button class="mt-3 text-sm font-medium text-secondary underline" @click="loadCourse(route.params.id)">Thử lại</button></section>
    <template v-else-if="course">
      <header class="border-b border-border pb-6"><p class="ui-eyebrow">{{ course.category }}</p><h1 class="ui-page-title mt-2">{{ course.title }}</h1><p class="mt-3 max-w-3xl whitespace-pre-line text-sm leading-7 text-muted">{{ course.description || 'Khóa học chưa có mô tả.' }}</p><dl class="mt-5 grid gap-4 sm:grid-cols-3"><div><dt class="text-xs text-muted">Nhà cung cấp</dt><dd class="mt-1 text-sm font-medium text-navy">{{ course.provider }}</dd></div><div><dt class="text-xs text-muted">Trình độ</dt><dd class="mt-1 text-sm font-medium text-navy">{{ course.level }}</dd></div><div><dt class="text-xs text-muted">Học phí</dt><dd class="mt-1 text-sm font-medium text-navy">{{ course.price == null ? 'Chưa có thông tin' : course.price === 0 ? 'Miễn phí' : new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(course.price) }}</dd></div></dl></header>
      <p v-if="categoryError" class="text-sm text-muted" role="status">{{ categoryError }}</p>
      <section v-if="enrollment"><h2 class="text-xl font-medium text-navy">Nội dung khóa học</h2><ol v-if="course.lessons.length" class="mt-3 divide-y divide-border border-y border-border"><li v-for="(lesson, index) in course.lessons" :key="lesson.id" class="py-5"><h3 class="font-medium text-navy">{{ index + 1 }}. {{ lesson.title }}</h3><p v-if="lesson.duration != null" class="mt-1 text-xs text-muted">Thời lượng: {{ lesson.duration }}</p><p v-if="lesson.content" class="mt-3 whitespace-pre-line text-sm leading-6 text-muted">{{ lesson.content }}</p><ul v-if="lesson.materials.length" class="mt-3 space-y-2"><li v-for="material in lesson.materials" :key="material.id" class="flex flex-wrap items-center gap-2 text-sm"><FileText :size="15" class="text-muted" aria-hidden="true" /><span class="text-navy">{{ material.title }}</span><a v-if="material.url" :href="material.url" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-secondary hover:underline">Mở tài liệu <ExternalLink :size="13" aria-hidden="true" /></a></li></ul></li></ol><p v-else class="mt-3 border-y border-border py-5 text-sm text-muted">Khóa học chưa có bài học.</p></section>
      <p v-else class="border-y border-border py-5 text-sm text-muted" role="status">Đăng ký khóa học để mở danh sách bài học và tài liệu.</p>
      <section class="border-t border-border pt-5">
        <p v-if="enrollmentError" class="mb-3 text-sm text-danger" role="alert">{{ enrollmentError }}</p>
        <p v-if="enrollmentSuccess" class="mb-3 text-sm text-success" role="status">{{ enrollmentSuccess }}</p>
        <RouterLink v-if="enrollment" :to="{ name: 'learning', params: { courseId: course.id } }" class="ui-button ui-button--primary">Tiếp tục học</RouterLink>
        <button v-else class="ui-button ui-button--primary" :disabled="enrollmentLoading" @click="enroll">{{ enrollmentLoading ? 'Đang đăng ký…' : 'Đăng ký khóa học' }}</button>
      </section>

      <section v-if="similarCourses.length" class="border-t border-border pt-6">
        <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 class="mt-1 text-xl font-semibold text-navy">Khóa học tương tự</h2>
          <button v-if="similarLoading" class="text-sm font-medium text-secondary underline" disabled>Đang tải…</button>
          <button v-else-if="similarError" class="text-sm font-medium text-secondary underline" @click="loadSimilarCourses(course.id, requestSequence)"><RefreshCw :size="14" aria-hidden="true" /> Thử lại</button>
        </div>
        <p v-if="similarLoading" class="py-4 text-sm text-muted" role="status">Đang tải khóa học tương tự…</p>
        <section v-else-if="similarError" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert">
          <p class="text-sm text-danger">{{ similarError }}</p>
        </section>
        <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <CourseCard v-for="item in similarCourses" :key="item.id" :course="item" />
        </div>
      </section>
      <section v-else-if="!similarLoading && !similarError && course" class="border-t border-border pt-6">
        <p class="text-sm text-muted">Chưa có khóa học tương tự được đề xuất.</p>
      </section>
    </template>
  </main>
</template>
