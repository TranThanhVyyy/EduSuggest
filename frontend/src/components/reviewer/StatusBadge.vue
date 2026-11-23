<script setup>
import { REVIEW_STATUS, REVIEW_STATUS_LABELS } from '@/constant/reviewStatus'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'

defineProps({
  status: { type: String, required: true },
})

const statusTones = {
  [REVIEW_STATUS.pending]: 'neutral',
  [REVIEW_STATUS.approved]: 'success',
  [REVIEW_STATUS.rejected]: 'danger',
  [REVIEW_STATUS.changesRequested]: 'warning',
}
</script>

<template>
  <UiStatusBadge :tone="statusTones[status] || 'neutral'">
    {{ REVIEW_STATUS_LABELS[status] || 'Chưa xác định' }}
  </UiStatusBadge>
</template>
