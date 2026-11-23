<script setup>
import { onMounted, ref } from 'vue'
import { ArrowRight } from 'lucide-vue-next'
import { getPendingExpertCourses, getExpertReviewHistory } from '@/service/expertApiService'

const pending = ref([])
const history = ref([])
const loading = ref(true)
const pendingError = ref('')
const historyError = ref('')

onMounted(async () => {
  const [pendingResult, historyResult] = await Promise.allSettled([
    getPendingExpertCourses(),
    getExpertReviewHistory(),
  ])
  if (pendingResult.status === 'fulfilled') pending.value = pendingResult.value
  else pendingError.value = pendingResult.reason.response?.data?.detail || 'Không thể tải hàng đợi kiểm duyệt.'
  if (historyResult.status === 'fulfilled') history.value = historyResult.value.slice(0, 5)
  else historyError.value = historyResult.reason.response?.data?.detail || 'Không thể tải lịch sử kiểm duyệt.'
  loading.value = false
})
</script>

<template>
  <main class="space-y-8">
    <header class="max-w-2xl border-b border-border pb-5"><p class="ui-eyebrow">Không gian chuyên gia</p><h1 class="ui-page-title mt-2">Kiểm duyệt khóa học</h1><p class="mt-2 text-sm leading-6 text-muted">Danh sách chờ xử lý và lịch sử được lấy từ API chuyên gia.</p></header>
    <p v-if="loading" class="py-4 text-sm text-muted" role="status">Đang tải…</p>
    <template v-else>
      <p v-if="pendingError" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ pendingError }}</p>
      <section class="flex flex-wrap items-baseline gap-x-3 gap-y-1"><span class="text-4xl font-light tabular-nums text-navy">{{ pendingError ? '—' : pending.length }}</span><span class="text-sm text-muted">khóa học đang chờ duyệt</span><RouterLink :to="{ name: 'reviewer-courses' }" class="ml-auto inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Mở hàng đợi <ArrowRight :size="15" aria-hidden="true" /> </RouterLink></section>
      <section class="border-t border-border pt-5"><div class="flex items-center justify-between"><h2 class="text-lg font-medium text-navy">Quyết định gần đây</h2><RouterLink :to="{ name: 'reviewer-history' }" class="text-sm font-medium text-secondary hover:underline">Toàn bộ lịch sử</RouterLink></div><p v-if="historyError" class="mt-3 text-sm text-danger" role="alert">{{ historyError }}</p><ul v-else-if="history.length" class="mt-3 divide-y divide-border border-y border-border"><li v-for="record in history" :key="record.id" class="flex flex-wrap justify-between gap-2 py-4"><span class="font-medium text-navy">{{ record.title }}</span><span class="text-sm text-muted">{{ record.note || 'Không có ghi chú' }}</span></li></ul><p v-else class="mt-3 text-sm text-muted">Chưa có quyết định trong lịch sử.</p></section>
      <p class="border-l-2 border-accent py-1 pl-4 text-sm leading-6 text-muted">Luồng kiểm duyệt tài liệu chưa có API; danh sách tài liệu đang được ẩn cho đến khi Backend hỗ trợ.</p>
    </template>
  </main>
</template>
