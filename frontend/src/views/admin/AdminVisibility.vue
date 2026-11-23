<script setup>
import { computed, onMounted, ref } from 'vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import api from '@/service/api'

const courses = ref([])
const loading = ref(true)
const busyId = ref(null)
const errorMessage = ref('')
const loadingError = ref('')
const search = ref('')
const visibleCourses = computed(() => courses.value.filter((course) => `${course.maKhoaHoc} ${course.tieuDe || ''}`.toLocaleLowerCase('vi').includes(search.value.trim().toLocaleLowerCase('vi'))))

async function loadCourses() {
  loading.value = true
  loadingError.value = ''
  errorMessage.value = ''
  try {
    const { data } = await api.get('/admin/courses')
    courses.value = data.filter((course) => course.trangThaiDuyet === 'APPROVED')
  } catch (error) {
    loadingError.value = error.response?.data?.detail || 'Không thể tải khóa học đã duyệt.'
  } finally { loading.value = false }
}

async function updateVisibility(course) {
  busyId.value = course.maKhoaHoc
  errorMessage.value = ''
  const next = course.trangThaiHienThi === 'VISIBLE' ? 'HIDDEN' : 'VISIBLE'
  try {
    const { data } = await api.patch(`/admin/courses/${course.maKhoaHoc}/visibility`, { trangThaiHienThi: next })
    Object.assign(course, data)
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể cập nhật trạng thái hiển thị.'
  } finally { busyId.value = null }
}
onMounted(loadCourses)
</script>

<template>
  <main class="space-y-6">
    <header class="max-w-2xl border-b border-border pb-5"><p class="ui-eyebrow">Quản lý nội dung</p><h1 class="ui-page-title mt-2">Hiển thị khóa học</h1><p class="mt-2 text-sm leading-6 text-muted"></p></header>
    <label class="block max-w-md text-sm font-medium text-navy">Tìm khóa học<input v-model="search" class="ui-input mt-2" type="search" placeholder="Tên khóa học hoặc mã"></label>
    <p v-if="loading" class="py-4 text-sm text-muted" role="status">Đang tải khóa học…</p>
    <p v-else-if="loadingError" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ loadingError }} <button class="underline" @click="loadCourses">Thử lại</button></p>
    <div v-else-if="visibleCourses.length" class="overflow-x-auto border-y border-border"><table class="w-full min-w-[620px] text-left text-sm"><thead class="border-b border-border text-xs text-muted"><tr><th class="py-3 pr-4 font-medium">Khóa học</th><th class="py-3 pr-4 font-medium">Kiểm duyệt</th><th class="py-3 pr-4 font-medium">Hiển thị</th><th class="py-3 text-right font-medium">Thao tác</th></tr></thead><tbody class="divide-y divide-border"><tr v-for="course in visibleCourses" :key="course.maKhoaHoc"><th scope="row" class="py-4 pr-4 font-medium text-navy">{{ course.tieuDe || `Khóa học #${course.maKhoaHoc}` }}</th><td class="py-4 pr-4"><UiStatusBadge tone="success">Đã phê duyệt</UiStatusBadge></td><td class="py-4 pr-4"><UiStatusBadge :tone="course.trangThaiHienThi === 'VISIBLE' ? 'success' : 'neutral'">{{ course.trangThaiHienThi === 'VISIBLE' ? 'Đang hiển thị' : 'Đang ẩn' }}</UiStatusBadge></td><td class="py-3 text-right"><UiButton size="sm" variant="outline" :loading="busyId === course.maKhoaHoc" @click="updateVisibility(course)">{{ course.trangThaiHienThi === 'VISIBLE' ? 'Ẩn' : 'Hiển thị' }}</UiButton></td></tr></tbody></table></div>
    <p v-else-if="!loading" class="py-6 text-sm text-muted">Không có khóa học đã duyệt phù hợp.</p>
    <p v-if="errorMessage" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p>
  </main>
</template>
