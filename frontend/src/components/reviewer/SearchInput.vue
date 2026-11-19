<script setup>
import { Search, X } from 'lucide-vue-next'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Tìm kiếm...' },
  label: { type: String, default: 'Tìm kiếm' },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <div class="relative block min-w-0">
    <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="17" aria-hidden="true" />
    <input
      :value="modelValue"
      type="search"
      :placeholder="placeholder"
      :aria-label="label"
      class="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-9 text-sm text-navy outline-none transition placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/15"
      @input="$emit('update:modelValue', $event.target.value)"
    >
    <button
      v-if="modelValue"
      type="button"
      class="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-muted hover:bg-background hover:text-navy"
      :aria-label="`Xóa ${label.toLocaleLowerCase('vi')}`"
      @click="$emit('update:modelValue', '')"
    >
      <X :size="15" aria-hidden="true" />
    </button>
  </div>
</template>
