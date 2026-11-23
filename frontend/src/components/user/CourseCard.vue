<script setup>
import { BookOpen, Clock3, GraduationCap, Star } from 'lucide-vue-next'

defineProps({
  course: { type: Object, required: true },
})

function priceLabel(price) {
  if (price == null) return 'Chưa có thông tin học phí'
  return price > 0 ? new Intl.NumberFormat('vi-VN').format(price) + ' ₫' : 'Miễn phí'
}
</script>

<template>
  <article class="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white transition hover:-translate-y-0.5 hover:shadow-md">
    <div v-if="course.coverImageUrl" class="h-40 overflow-hidden bg-background">
      <img :src="course.coverImageUrl" :alt="course.title" class="h-full w-full object-cover">
    </div>
    <div v-else class="flex h-40 items-center justify-center bg-primary/5 text-primary">
      <BookOpen :size="40" aria-hidden="true" />
    </div>
    <div class="flex flex-1 flex-col p-4">
      <div class="flex flex-wrap items-center gap-2 text-xs">
        <span class="rounded-full bg-primary/10 px-2.5 py-1 font-semibold text-primary">{{ course.category || 'Chưa phân loại' }}</span>
        <span v-if="course.level" class="rounded-full bg-background px-2.5 py-1 text-muted">{{ course.level }}</span>
      </div>
      <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }" class="mt-3 line-clamp-2 text-base font-bold text-navy hover:text-primary">
        {{ course.title }}
      </RouterLink>
      <p class="mt-2 line-clamp-2 text-sm leading-5 text-muted">{{ course.description }}</p>
      <div class="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
        <span v-if="course.provider" class="inline-flex items-center gap-1"><GraduationCap :size="14" aria-hidden="true" />{{ course.provider }}</span>
        <span v-if="course.duration" class="inline-flex items-center gap-1"><Clock3 :size="14" aria-hidden="true" />{{ course.duration }}</span>
        <span v-if="course.rating != null" class="inline-flex items-center gap-1"><Star :size="14" class="text-accent" aria-hidden="true" />{{ course.rating }}<span v-if="course.reviewCount">({{ course.reviewCount }})</span></span>
      </div>
      <div class="mt-auto flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <span class="text-sm font-bold text-navy">{{ priceLabel(course.price) }}</span>
        <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }" class="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:opacity-90">Xem chi tiết</RouterLink>
      </div>
    </div>
  </article>
</template>
