<script setup>
import { computed, ref } from 'vue'
import { SlidersHorizontal } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import { getPublicCourses, getPublicMaterials } from '@/service/userService'

const query = ref('')
const format = ref('')
const materials = computed(() => getPublicMaterials().map((material) => {
  const course = getPublicCourses().find((item) => item.id === material.courseId)
  const lesson = course?.chapters.flatMap((chapter) => chapter.lessons).find((item) => item.id === material.lessonId)
  return {
    ...material,
    courseTitle: course?.title || 'Chưa có thông tin',
    lessonTitle: lesson?.title || 'Tài liệu khóa học',
    sizeLabel: material.sizeBytes ? `${Math.round(material.sizeBytes / 1024)} KB` : 'Chưa có dữ liệu',
  }
}))
const formats = computed(() => [...new Set(materials.value.map((material) => material.format))].sort())
const filteredMaterials = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return materials.value.filter((material) =>
    (!format.value || material.format === format.value)
    && (!search || `${material.title} ${material.description} ${material.type} ${material.format} ${material.courseTitle}`.toLocaleLowerCase('vi').includes(search)),
  )
})

</script>

<template>
  <div class="space-y-5">
    <section><p class="text-sm text-muted">Thư viện học tập</p><h1 class="mt-1 text-2xl font-bold text-navy">Tài liệu học tập</h1><p class="mt-2 text-sm text-muted">Chỉ liệt kê tài liệu mẫu có quyền truy cập. Không tạo URL xem trước hoặc tải xuống nếu chưa có tệp.</p></section>
    <section class="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-[minmax(0,1fr)_220px]">
      <SearchInput v-model="query" label="Tìm kiếm tài liệu" placeholder="Tên, mô tả, loại hoặc khóa học..."/>
      <label class="sr-only" for="material-format">Lọc định dạng</label>
      <select id="material-format" v-model="format" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary"><option value="">Mọi định dạng</option><option v-for="item in formats" :key="item">{{ item }}</option></select>
    </section>
    <div class="flex items-center gap-2 text-sm text-muted"><SlidersHorizontal :size="16" aria-hidden="true" /> {{ filteredMaterials.length }} tài liệu phù hợp</div>
    <div v-if="filteredMaterials.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><MaterialCard v-for="material in filteredMaterials" :key="material.id" :material="material" /></div>
    <div v-else class="rounded-2xl border border-slate-200 bg-white"><EmptyState title="Không tìm thấy tài liệu" description="Thử từ khóa hoặc định dạng khác." /></div>
  </div>
</template>
