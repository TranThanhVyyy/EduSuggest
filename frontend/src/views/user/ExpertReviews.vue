<script setup>
import { computed, reactive, ref } from 'vue'
import { MessageSquareText, Star } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getExpertReviewHistory, getExperts, submitExpertReview } from '@/service/userService'

const experts = computed(() => getExperts())
const reviews = computed(() => getExpertReviewHistory())
const selectedExpert = ref(null)
const errorMessage = ref('')
const toastMessage = ref('')
const form = reactive({ rating: 0, comment: '' })

function openReview(expert) {
  selectedExpert.value = expert
  form.rating = 0
  form.comment = ''
  errorMessage.value = expert.canReview ? '' : (expert.eligibilityMessage || 'Điều kiện đánh giá chưa được xác nhận bởi Backend.')
}

function submit() {
  if (!selectedExpert.value) return
  try {
    submitExpertReview(selectedExpert.value.id, form)
    selectedExpert.value = null
    errorMessage.value = ''
    toastMessage.value = 'Đã gửi đánh giá mẫu trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể gửi đánh giá.'
  }
}
</script>

<template>
  <div class="space-y-5">
    <section><p class="text-sm text-muted">Cộng đồng</p><h1 class="mt-1 text-2xl font-bold text-navy">Đánh giá chuyên gia</h1><p class="mt-2 text-sm leading-6 text-muted">Chỉ có thể đánh giá khi Backend xác nhận đủ điều kiện. Dữ liệu demo hiện chưa xác nhận chuyên gia nào đủ điều kiện.</p></section>
    <section class="grid gap-4 md:grid-cols-2">
      <article v-for="expert in experts" :key="expert.id" class="rounded-2xl border border-slate-200 bg-white p-5">
        <div class="flex items-start gap-3"><span class="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">{{ expert.fullName.split(' ').slice(-1)[0]?.[0] }}</span><div class="min-w-0"><h2 class="font-bold text-navy">{{ expert.fullName }}</h2><p class="mt-1 text-xs text-muted">{{ expert.specialties.join(' · ') }}</p></div></div>
        <p class="mt-3 text-sm leading-6 text-muted">{{ expert.introduction }}</p>
        <p class="mt-3 inline-flex items-center gap-1 text-xs text-muted"><Star :size="14" aria-hidden="true" />{{ expert.rating == null ? 'Chưa có đánh giá' : `${expert.rating} / 5 · ${expert.reviewCount} lượt` }}</p>
        <button type="button" class="mt-4 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:border-primary hover:text-primary" @click="openReview(expert)">Kiểm tra điều kiện đánh giá</button>
        <p v-if="selectedExpert?.id === expert.id" class="mt-3 rounded-lg bg-background p-3 text-xs leading-5 text-muted">{{ expert.eligibilityMessage }}</p>
      </article>
      <div v-if="!experts.length" class="rounded-2xl border border-slate-200 bg-white md:col-span-2"><EmptyState title="Chưa có chuyên gia" description="Danh sách chuyên gia sẽ xuất hiện khi Backend cung cấp dữ liệu." /></div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5">
      <div class="flex items-center gap-2"><MessageSquareText :size="18" class="text-primary" aria-hidden="true" /><h2 class="font-bold text-navy">Lịch sử đánh giá của bạn</h2></div>
      <ul v-if="reviews.length" class="mt-4 divide-y divide-slate-100"><li v-for="review in reviews" :key="review.id" class="py-3"><p class="font-semibold text-navy">{{ experts.find((expert) => expert.id === review.expertId)?.fullName || 'Chuyên gia' }} · {{ review.rating }}/5 sao</p><p class="mt-1 text-sm text-muted">{{ review.comment }}</p></li></ul>
      <p v-else class="mt-3 text-sm text-muted">Chưa có đánh giá nào được gửi.</p>
      <form v-if="selectedExpert?.canReview" class="mt-5 space-y-3 border-t border-slate-100 pt-4" @submit.prevent="submit">
        <label class="block text-sm font-semibold text-navy">Số sao
          <select v-model.number="form.rating" required class="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-primary"><option :value="0" disabled>Chọn số sao</option><option v-for="star in 5" :key="star" :value="star">{{ star }} sao</option></select>
        </label>
        <label class="block text-sm font-semibold text-navy">Nhận xét
          <textarea v-model="form.comment" required rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary"></textarea>
        </label>
        <p v-if="errorMessage" class="text-sm text-primary" role="alert">{{ errorMessage }}</p>
        <button class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white">Gửi đánh giá</button>
      </form>
      <p v-else-if="selectedExpert" class="mt-4 text-xs text-muted">Biểu mẫu chưa khả dụng cho đến khi có xác nhận điều kiện từ Backend.</p>
    </section>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
