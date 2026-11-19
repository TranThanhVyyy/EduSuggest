<script setup>
import { REVIEW_STATUS, REVIEW_STATUS_LABELS } from '@/constant/reviewStatus'

defineProps({
  status: { type: String, required: true },
})

const statusClasses = {
  [REVIEW_STATUS.pending]: 'border-slate-200 bg-background text-muted',
  [REVIEW_STATUS.inReview]: 'border-primary/20 bg-primary/10 text-primary',
  [REVIEW_STATUS.approved]: 'border-accent/20 bg-accent/10 text-accent',
  [REVIEW_STATUS.rejected]: 'border-navy/15 bg-navy/5 text-navy',
  [REVIEW_STATUS.changesRequested]: 'border-primary/20 bg-primary/5 text-primary',
}
</script>

<template>
  <span class="inline-flex whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-semibold" :class="statusClasses[status] || statusClasses[REVIEW_STATUS.pending]">
    {{ REVIEW_STATUS_LABELS[status] || 'Chưa xác định' }}
  </span>
</template>
