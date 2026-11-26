<script setup>
import { computed } from 'vue'

const REASON_LABELS = Object.freeze({
  CONTENT_SIMILARITY: 'Nội dung tương đồng',
  SAME_CATEGORY: 'Cùng danh mục',
  SIMILAR_LEVEL: 'Cùng trình độ',
  SAME_LESSON: 'Liên quan bài học',
  RECENT_COURSE: 'Khóa học mới cập nhật',
  RECENT_MATERIAL: 'Tài liệu mới cập nhật',
})

const props = defineProps({
  reasonCodes: {
    type: Array,
    default: () => [],
  },
  maxVisible: {
    type: Number,
    default: 2,
  },
})

const badges = computed(() => {
  if (!Array.isArray(props.reasonCodes) || !props.reasonCodes.length) return []
  const seen = new Set()
  const items = []
  const limit = Math.max(0, Math.min(props.maxVisible, 2))
  for (const rawCode of props.reasonCodes) {
    const code = typeof rawCode === 'string' ? rawCode.trim().toUpperCase() : ''
    if (!code || seen.has(code) || !REASON_LABELS[code]) continue
    seen.add(code)
    items.push({
      code,
      label: REASON_LABELS[code],
      isRecent: code === 'RECENT_COURSE' || code === 'RECENT_MATERIAL',
    })
    if (items.length >= limit) break
  }
  return items
})
</script>

<template>
  <div v-if="badges.length" class="flex flex-wrap items-center gap-1.5" aria-label="Lý do gợi ý">
    <span
      v-for="badge in badges"
      :key="badge.code"
      :class="[
        'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium border',
        badge.isRecent
          ? 'border-amber/25 bg-amber/10 text-amber-dark'
          : 'border-teal/25 bg-teal/10 text-teal-dark',
      ]"
    >
      {{ badge.label }}
    </span>
  </div>
</template>
