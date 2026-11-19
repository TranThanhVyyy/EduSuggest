<script setup>
import { Inbox } from 'lucide-vue-next'

defineProps({
  title: { type: String, default: 'Chưa có nội dung' },
  description: { type: String, default: 'Nội dung sẽ xuất hiện tại đây khi có dữ liệu phù hợp.' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 py-14 text-center">
    <span class="flex size-12 items-center justify-center rounded-2xl bg-background text-muted">
      <Inbox :size="23" aria-hidden="true" />
    </span>
    <h2 class="mt-4 text-base font-semibold text-navy">{{ title }}</h2>
    <p class="mt-1 max-w-md text-sm leading-6 text-muted">{{ description }}</p>
  </div>
</template>
