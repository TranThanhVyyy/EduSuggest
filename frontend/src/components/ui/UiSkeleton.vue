<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'text', // 'text' | 'image' | 'card' | 'table' | 'circle' | 'rect'
    validator: (v) => ['text', 'image', 'card', 'table', 'circle', 'rect'].includes(v),
  },
  lines: {
    type: Number,
    default: 3,
  },
  width: {
    type: String,
    default: '',
  },
  height: {
    type: String,
    default: '',
  },
  rounded: {
    type: String,
    default: '',
  },
})

const customStyle = computed(() => {
  const style = {}
  if (props.width) style.width = props.width
  if (props.height) style.height = props.height
  if (props.rounded) style.borderRadius = props.rounded
  return style
})
</script>

<template>
  <div v-if="variant === 'text'" class="space-y-2.5" role="status" aria-label="Đang tải dữ liệu">
    <div
      v-for="index in lines"
      :key="index"
      class="es-skeleton h-4"
      :style="{ width: index === lines ? '60%' : '100%' }"
    />
  </div>

  <div
    v-else-if="variant === 'circle'"
    class="es-skeleton shrink-0 rounded-full"
    :style="customStyle || { width: '40px', height: '40px' }"
    role="status"
    aria-label="Đang tải dữ liệu"
  />

  <div
    v-else-if="variant === 'image'"
    class="es-skeleton w-full rounded-lg"
    :style="customStyle || { height: '180px' }"
    role="status"
    aria-label="Đang tải hình ảnh"
  />

  <div
    v-else-if="variant === 'card'"
    class="bento-card space-y-4"
    role="status"
    aria-label="Đang tải thẻ dữ liệu"
  >
    <div class="es-skeleton h-36 w-full rounded-md" />
    <div class="es-skeleton h-5 w-3/4" />
    <div class="space-y-2">
      <div class="es-skeleton h-3.5 w-full" />
      <div class="es-skeleton h-3.5 w-4/5" />
    </div>
    <div class="flex items-center justify-between pt-2">
      <div class="es-skeleton h-4 w-20" />
      <div class="es-skeleton h-7 w-24 rounded-md" />
    </div>
  </div>

  <div
    v-else-if="variant === 'table'"
    class="space-y-3"
    role="status"
    aria-label="Đang tải bảng dữ liệu"
  >
    <div class="es-skeleton h-8 w-full rounded" />
    <div v-for="i in lines" :key="i" class="es-skeleton h-10 w-full rounded" />
  </div>

  <div
    v-else
    class="es-skeleton"
    :style="customStyle"
    role="status"
    aria-label="Đang tải"
  />
</template>
