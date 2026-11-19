<script setup>
import { CheckCircle2, X } from 'lucide-vue-next'

defineProps({
  message: { type: String, default: '' },
})

defineEmits(['close'])
</script>

<template>
  <div v-if="message" class="fixed bottom-4 right-4 z-50 flex max-w-[calc(100vw-2rem)] items-start gap-3 rounded-xl border border-accent/20 bg-white px-4 py-3 shadow-lg" role="status" aria-live="polite">
    <CheckCircle2 class="mt-0.5 shrink-0 text-accent" :size="18" aria-hidden="true" />
    <p class="text-sm font-medium text-navy">{{ message }}</p>
    <button type="button" class="-mr-1 -mt-1 flex size-7 shrink-0 items-center justify-center rounded-md text-muted hover:bg-background" aria-label="Đóng thông báo" @click="$emit('close')">
      <X :size="15" aria-hidden="true" />
    </button>
  </div>
</template>
