<script setup>
import { computed, onMounted, ref } from 'vue'
import { BookOpen, ExternalLink } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import { fetchLearningHistory } from '@/service/userApiService'

const query = ref('')
const sortOrder = ref('newest')
const history = ref([])
const loading = ref(true)
const error = ref('')
const entries = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return history.value.filter((entry) => !search || `${entry.course.title} ${entry.lesson.title}`.toLocaleLowerCase('vi').includes(search))
    .sort((a, b) => sortOrder.value === 'newest' ? new Date(b.createdAt || 0) - new Date(a.createdAt || 0) : new Date(a.createdAt || 0) - new Date(b.createdAt || 0))
})
async function load() {
  loading.value = true
  error.value = ''
  try { history.value = await fetchLearningHistory() }
  catch (cause) { error.value = cause.response?.data?.detail || 'Không thể tải lịch sử học tập.' }
  finally { loading.value = false }
}
function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
onMounted(load)
</script>

<template>
  <div class="space-y-5">
    <section class="border-b border-border pb-5"><p class="ui-eyebrow">Học tập</p><h1 class="ui-page-title mt-2">Lịch sử học tập</h1><p class="mt-2 text-sm text-muted">Các bài học đã được bạn đánh dấu hoàn thành.</p></section>
    <p v-if="loading" class="py-5 text-sm text-muted" role="status">Đang tải lịch sử…</p>
    <section v-else-if="error" class="max-w-2xl border-l-2 border-danger py-1 pl-4" role="alert"><p class="text-sm text-danger">{{ error }}</p><button class="mt-3 text-sm text-secondary underline" @click="load">Thử lại</button></section>
    <section v-else-if="history.length" class="overflow-hidden rounded-xl border border-border bg-white">
      <div class="grid gap-3 border-b border-border p-4 md:grid-cols-[minmax(0,1fr)_190px]"><SearchInput v-model="query" label="Tìm lịch sử học tập" placeholder="Tên khóa học hoặc bài học"/><label class="sr-only" for="history-sort">Sắp xếp lịch sử</label><select id="history-sort" v-model="sortOrder" class="rounded-lg border border-border bg-white px-3 py-2.5 text-sm text-navy"><option value="newest">Gần đây nhất</option><option value="oldest">Cũ nhất</option></select></div>
      <div v-if="entries.length" class="divide-y divide-border"><article v-for="entry in entries" :key="entry.id" class="flex flex-wrap items-center justify-between gap-3 p-4"><div class="flex min-w-0 items-start gap-3"><BookOpen :size="18" class="mt-1 shrink-0 text-muted" aria-hidden="true"/><div class="min-w-0"><h2 class="font-semibold text-navy">{{ entry.course.title }}</h2><p class="mt-1 text-sm text-muted">{{ entry.lesson.title }} · Hoàn thành {{ formatDate(entry.createdAt) }}</p></div></div><RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Mở khóa học <ExternalLink :size="14" aria-hidden="true"/></RouterLink></article></div>
      <EmptyState v-else title="Không có lịch sử phù hợp" description="Thay đổi từ khóa tìm kiếm để xem các bài học đã hoàn thành."/>
    </section>
    <section v-else class="max-w-2xl border-y border-border py-3"><EmptyState title="Chưa có lịch sử học tập" description="Bài học hoàn thành sẽ được lưu tại đây." /></section>
  </div>
</template>
