<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/service/api'

const route = useRoute()
const resource = computed(() => route.meta.adminResource)
const course = ref(null)
const loading = ref(false)
const errorMessage = ref('')

async function loadCourse() {
  course.value = null
  errorMessage.value = ''
  if (resource.value !== 'courses') {
    errorMessage.value = `Backend chưa cung cấp API chi tiết ${resource.value === 'lessons' ? 'bài học' : 'tài liệu'} cho quản trị viên.`
    return
  }
  loading.value = true
  try {
    const { data } = await api.get('/admin/courses')
    course.value = data.find((record) => String(record.maKhoaHoc) === String(route.params.id)) || null
    if (!course.value) errorMessage.value = 'Không tìm thấy khóa học.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải khóa học.'
  } finally { loading.value = false }
}
watch(() => [route.params.id, resource.value], loadCourse, { immediate: true })
</script>

<template><main class="max-w-3xl space-y-5"><RouterLink :to="{ name: resource === 'courses' ? 'admin-courses' : 'admin-dashboard' }" class="text-sm font-medium text-secondary hover:underline">← Quay lại</RouterLink><header class="border-b border-border pb-5"><p class="ui-eyebrow">Quản lý nội dung</p><h1 class="ui-page-title mt-2">Chi tiết {{ resource === 'courses' ? 'khóa học' : resource === 'lessons' ? 'bài học' : 'tài liệu' }}</h1></header><p v-if="loading" class="text-sm text-muted" role="status">Đang tải…</p><p v-else-if="errorMessage" class="border-l-2 border-accent py-1 pl-4 text-sm leading-6 text-muted" role="status">{{ errorMessage }}</p><template v-else-if="course"><h2 class="text-xl font-medium text-navy">{{ course.tieuDe || 'Chưa có tiêu đề' }}</h2><p class="whitespace-pre-line text-sm leading-6 text-muted">{{ course.moTa || 'Chưa có mô tả.' }}</p><dl class="grid gap-4 border-y border-border py-4 sm:grid-cols-2"><div><dt class="text-xs text-muted">Mã khóa học</dt><dd class="mt-1 text-sm text-navy">{{ course.maKhoaHoc }}</dd></div><div><dt class="text-xs text-muted">Trạng thái kiểm duyệt</dt><dd class="mt-1 text-sm text-navy">{{ course.trangThaiDuyet || '—' }}</dd></div></dl></template></main></template>
