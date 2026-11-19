<script setup>
import { computed, ref } from 'vue'
import { ArrowUpDown, BookOpen } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import { getLearningHistory } from '@/service/userService'

const query = ref('')
const status = ref('')
const sortOrder = ref('newest')
const entries = computed(() => {
  const search = query.value.trim().toLocaleLowerCase('vi')
  return getLearningHistory()
    .filter(({ course, enrollment }) => {
      const matchesSearch = !search || `${course.title} ${course.category} ${course.provider}`.toLocaleLowerCase('vi').includes(search)
      return matchesSearch && (!status.value || enrollment.status === status.value)
    })
    .sort((first, second) => {
      const dateA = new Date(first.enrollment.lastAccessedAt || first.enrollment.enrolledAt).getTime()
      const dateB = new Date(second.enrollment.lastAccessedAt || second.enrollment.enrolledAt).getTime()
      return sortOrder.value === 'newest' ? dateB - dateA : dateA - dateB
    })
})

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
</script>

<template>
  <div class="space-y-5">
    <section><p class="text-sm text-muted">Học tập</p><h1 class="mt-1 text-2xl font-bold text-navy">Lịch sử học tập</h1><p class="mt-2 text-sm text-muted">Lọc và sắp xếp các khóa học đã đăng ký trong dữ liệu mẫu.</p></section>
    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(0,1fr)_190px_190px]">
        <SearchInput v-model="query" label="Tìm lịch sử học tập" placeholder="Tên khóa học, danh mục..."/>
        <label class="sr-only" for="history-status">Lọc theo trạng thái</label>
        <select id="history-status" v-model="status" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary"><option value="">Mọi trạng thái</option><option value="in_progress">Đang học</option><option value="completed">Hoàn thành</option></select>
        <label class="sr-only" for="history-sort">Sắp xếp lịch sử</label>
        <select id="history-sort" v-model="sortOrder" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary"><option value="newest">Gần đây nhất</option><option value="oldest">Cũ nhất</option></select>
      </div>
      <div v-if="entries.length" class="divide-y divide-slate-100">
        <article v-for="entry in entries" :key="entry.enrollment.id" class="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div class="flex min-w-0 items-start gap-3"><span class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-background text-muted"><BookOpen :size="18" aria-hidden="true" /></span><div class="min-w-0"><h2 class="font-semibold text-navy">{{ entry.course.title }}</h2><p class="mt-1 text-xs text-muted">{{ entry.course.category }} · Đăng ký {{ formatDate(entry.enrollment.enrolledAt) }} · Học gần nhất {{ formatDate(entry.enrollment.lastAccessedAt) }}</p><p class="mt-1 text-xs text-muted">{{ entry.progress.completedLessons }}/{{ entry.progress.totalLessons }} bài hoàn thành · {{ entry.progress.percentage }}%</p></div></div>
          <RouterLink :to="{ name: 'learning', params: { courseId: entry.course.id } }" class="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:border-primary hover:text-primary"><ArrowUpDown :size="14" aria-hidden="true" />{{ entry.enrollment.status === 'completed' ? 'Xem lại' : 'Tiếp tục học' }}</RouterLink>
        </article>
      </div>
      <EmptyState v-else title="Không có lịch sử phù hợp" description="Thay đổi bộ lọc hoặc đăng ký khóa học để bắt đầu." />
    </section>
  </div>
</template>
