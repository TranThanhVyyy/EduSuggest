<script setup>
import { computed, onMounted, ref } from 'vue'
import { Eye } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getPendingExpertCourses } from '@/service/expertApiService'

const props = defineProps({ kind: { type: String, required: true } })
const items = ref([])
const loading = ref(true)
const errorMessage = ref('')
const isCourse = computed(() => props.kind === 'course')

async function loadItems() {
  loading.value = true
  errorMessage.value = ''
  try {
    items.value = isCourse.value ? await getPendingExpertCourses() : []
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải danh sách. Hãy thử lại.'
  } finally {
    loading.value = false
  }
}

onMounted(loadItems)
</script>

<template>
  <main class="space-y-6">
    <header class="max-w-2xl border-b border-border pb-5">
      <p class="ui-eyebrow">Kiểm duyệt</p>
      <h1 class="ui-page-title mt-2">{{ isCourse ? 'Khóa học chờ duyệt' : 'Tài liệu chờ duyệt' }}</h1>
      <p class="mt-2 text-sm leading-6 text-muted">{{ isCourse ? 'Danh sách được tải từ hệ thống kiểm duyệt.' : 'Backend hiện chưa cung cấp API để chuyên gia duyệt tài liệu.' }}</p>
    </header>
    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải danh sách…</p>
    <p v-else-if="errorMessage" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p>
    <section v-else-if="!isCourse" class="border-l-2 border-accent py-1 pl-4" role="status"><h2 class="font-medium text-navy">Chưa có luồng duyệt tài liệu</h2><p class="mt-2 text-sm text-muted">Danh sách và thao tác duyệt tài liệu chưa được kết nối với Backend.</p></section>
    <section v-else-if="items.length" class="overflow-x-auto border-y border-border">
      <table class="w-full min-w-[620px] text-left text-sm">
        <thead class="border-b border-border text-xs text-muted"><tr><th class="py-3 pr-4 font-medium">Khóa học</th><th class="py-3 pr-4 font-medium">ID</th><th class="py-3 pr-4 font-medium">Cập nhật</th><th class="py-3 pr-4 font-medium">Trạng thái</th><th class="py-3 font-medium">Chi tiết</th></tr></thead>
        <tbody class="divide-y divide-border"><tr v-for="item in items" :key="item.id"><th scope="row" class="py-4 pr-4 font-medium text-navy">{{ item.title }}</th><td class="py-4 pr-4 text-muted">{{ item.id }}</td><td class="py-4 pr-4 text-muted">{{ item.submittedAt ? new Date(item.submittedAt).toLocaleDateString('vi-VN') : '—' }}</td><td class="py-4 pr-4"><StatusBadge :status="item.status" /></td><td class="py-4"><RouterLink :to="{ name: 'reviewer-course-detail', params: { id: item.id } }" class="inline-flex items-center gap-2 font-medium text-secondary hover:underline"><Eye :size="15" aria-hidden="true" /> Mở</RouterLink></td></tr></tbody>
      </table>
    </section>
    <EmptyState v-else-if="!loading && !errorMessage" title="Không có khóa học chờ duyệt" description="Các khóa học đang chờ chuyên gia sẽ xuất hiện tại đây." />
    <button v-if="errorMessage" type="button" class="text-sm font-medium text-secondary underline" @click="loadItems">Thử tải lại</button>
  </main>
</template>
