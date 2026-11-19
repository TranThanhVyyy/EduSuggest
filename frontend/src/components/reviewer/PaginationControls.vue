<script setup>
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

defineProps({
  modelValue: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  totalItems: { type: Number, required: true },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3">
    <p class="text-xs text-muted">
      Trang {{ modelValue }} / {{ totalPages }} · {{ totalItems }} kết quả
    </p>
    <div class="flex items-center gap-2">
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy transition hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="modelValue <= 1"
        @click="$emit('update:modelValue', modelValue - 1)"
      >
        <ChevronLeft :size="15" aria-hidden="true" /> Trước
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy transition hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="modelValue >= totalPages"
        @click="$emit('update:modelValue', modelValue + 1)"
      >
        Sau <ChevronRight :size="15" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
