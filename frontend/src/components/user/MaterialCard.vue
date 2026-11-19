<script setup>
import { Download, FileText } from 'lucide-vue-next'

defineProps({
  material: { type: Object, required: true },
})
</script>

<template>
  <article class="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-4">
    <div class="flex items-start gap-3">
      <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent"><FileText :size="20" aria-hidden="true" /></span>
      <div class="min-w-0 flex-1">
        <RouterLink :to="{ name: 'material-detail', params: { id: material.id } }" class="line-clamp-2 font-bold text-navy hover:text-primary">{{ material.title }}</RouterLink>
        <p class="mt-1 text-xs text-muted">{{ material.type }} · {{ material.format }}</p>
      </div>
    </div>
    <p class="mt-3 line-clamp-2 text-sm leading-5 text-muted">{{ material.description }}</p>
    <div class="mt-4 space-y-1 text-xs text-muted">
      <p>Khóa học: {{ material.courseTitle || 'Chưa có thông tin' }}</p>
      <p>Bài học: {{ material.lessonTitle || 'Tài liệu khóa học' }}</p>
      <p>Dung lượng: {{ material.sizeLabel || 'Chưa có dữ liệu' }}</p>
    </div>
    <div class="mt-auto flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
      <span class="text-xs text-muted">{{ material.provider }}</span>
      <RouterLink :to="{ name: 'material-detail', params: { id: material.id } }" class="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:border-primary hover:text-primary">
        <Download :size="14" aria-hidden="true" /> Xem
      </RouterLink>
    </div>
  </article>
</template>
