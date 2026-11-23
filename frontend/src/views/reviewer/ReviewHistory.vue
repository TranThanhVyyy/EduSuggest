<script setup>
import { onMounted, ref } from 'vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getExpertReviewHistory } from '@/service/expertApiService'

const history = ref([])
const loading = ref(true)
const errorMessage = ref('')

async function loadHistory() {
  loading.value = true
  errorMessage.value = ''
  try { history.value = await getExpertReviewHistory() }
  catch (error) { errorMessage.value = error.response?.data?.detail || 'Không thể tải lịch sử kiểm duyệt.' }
  finally { loading.value = false }
}
onMounted(loadHistory)
</script>

<template>
  <main class="space-y-6">
    <header class="max-w-2xl border-b border-border pb-5"><p class="ui-eyebrow">Báo cáo</p><h1 class="ui-page-title mt-2">Lịch sử kiểm duyệt</h1><p class="mt-2 text-sm text-muted">Các quyết định đã lưu qua API chuyên gia.</p></header>
    <p v-if="loading" class="py-4 text-sm text-muted" role="status">Đang tải lịch sử…</p>
    <p v-else-if="errorMessage" class="border-l-2 border-danger py-2 pl-3 text-sm text-danger" role="alert">{{ errorMessage }} <button class="ml-2 underline" @click="loadHistory">Thử lại</button></p>
    <table v-else-if="history.length" class="w-full border-y border-border text-left text-sm"><thead class="border-b border-border text-xs text-muted"><tr><th class="py-3 pr-4 font-medium">Khóa học</th><th class="py-3 pr-4 font-medium">Kết quả</th><th class="py-3 pr-4 font-medium">Ngày ghi nhận</th><th class="py-3 font-medium">Ghi chú</th></tr></thead><tbody class="divide-y divide-border"><tr v-for="record in history" :key="record.id"><th class="py-4 pr-4 font-medium text-navy">{{ record.title }}</th><td class="py-4 pr-4"><StatusBadge :status="record.status" /></td><td class="py-4 pr-4 text-muted">{{ record.reviewedAt ? new Date(record.reviewedAt).toLocaleString('vi-VN') : '—' }}</td><td class="py-4 text-muted">{{ record.note || '—' }}</td></tr></tbody></table>
    <p v-else-if="!loading" class="py-6 text-sm text-muted">Chưa có lịch sử kiểm duyệt.</p>
  </main>
</template>
