<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, BookOpen, Clock3, FileEdit, Plus, Send, ShieldCheck } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
} from '@/service/providerApiService'
import { loadProviderCourses, providerErrorMessage } from '@/service/providerApiService'

const courses = ref([])
const loadError = ref('')
const dashboard = computed(() => ({
  total: courses.value.length,
  statusCounts: Object.fromEntries(statusCards.map(({ key }) => [key, courses.value.filter((course) => course.status === key).length])),
  recentCourses: [...courses.value].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)).slice(0, 5),
}))
onMounted(async () => {
  try {
    courses.value = await loadProviderCourses()
  } catch (error) {
    loadError.value = providerErrorMessage(error, 'Không thể tải số liệu khóa học.')
  }
})
const statusCards = [
  { key: PROVIDER_STATUS.draft, label: 'Bản nháp', icon: FileEdit },
  { key: PROVIDER_STATUS.pending, label: 'Chờ kiểm duyệt', icon: Clock3 },
  { key: PROVIDER_STATUS.approved, label: 'Đã phê duyệt', icon: ShieldCheck },
  { key: PROVIDER_STATUS.rejected, label: 'Bị từ chối', icon: FileEdit },
  { key: PROVIDER_STATUS.changesRequested, label: 'Cần chỉnh sửa', icon: FileEdit },
]

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}

function statusClass(status) {
  if (status === PROVIDER_STATUS.approved) return 'bg-accent/10 text-accent'
  if (status === PROVIDER_STATUS.pending) return 'bg-primary/10 text-primary'
  if (status === PROVIDER_STATUS.rejected || status === PROVIDER_STATUS.changesRequested) return 'bg-slate-100 text-navy'
  return 'bg-background text-muted'
}
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Tổng quan người cung cấp</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Dashboard</h2>
        <p class="mt-2 text-sm leading-6 text-muted">Theo dõi khóa học của bạn và trạng thái kiểm duyệt từ Backend.</p>
      </div>
      <RouterLink :to="{ name: 'provider-course-create' }" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
        <Plus :size="17" aria-hidden="true" /> Tạo khóa học
      </RouterLink>
    </section>

    <p v-if="loadError" class="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-primary" role="alert">{{ loadError }}</p>
    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Thống kê khóa học">
      <article class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="flex items-center justify-between text-muted"><span class="text-sm">Tổng khóa học</span><BookOpen :size="18" aria-hidden="true" /></div>
        <p class="mt-3 text-2xl font-bold text-navy">{{ dashboard.total }}</p>
      </article>
      <article v-for="card in statusCards" :key="card.key" class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="flex items-center justify-between text-muted"><span class="text-sm">{{ card.label }}</span><component :is="card.icon" :size="18" aria-hidden="true" /></div>
        <p class="mt-3 text-2xl font-bold text-navy">{{ dashboard.statusCounts[card.key] || 0 }}</p>
      </article>
    </section>

    <section class="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
      <article class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div class="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <h3 class="font-bold text-navy">Khóa học gần đây</h3>
            <p class="mt-1 text-xs text-muted">Sắp xếp theo thời gian cập nhật.</p>
          </div>
          <RouterLink :to="{ name: 'provider-courses' }" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">Tất cả <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
        </div>
        <div v-if="dashboard.recentCourses.length" class="divide-y divide-slate-100">
          <div v-for="course in dashboard.recentCourses" :key="course.id" class="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div class="min-w-0">
              <RouterLink :to="{ name: 'provider-course-detail', params: { id: course.id } }" class="block truncate text-sm font-semibold text-navy hover:text-primary">{{ course.title || 'Khóa học chưa đặt tên' }}</RouterLink>
              <p class="mt-1 text-xs text-muted">{{ course.category || 'Chưa chọn danh mục' }} · Cập nhật {{ formatDate(course.updatedAt) }}</p>
            </div>
            <span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold" :class="statusClass(course.status)">{{ PROVIDER_STATUS_LABELS[course.status] }}</span>
          </div>
        </div>
        <p v-else class="p-6 text-sm text-muted">Chưa có khóa học nào.</p>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 class="font-bold text-navy">Hoạt động gần đây</h3>
        <p class="mt-1 text-xs text-muted">Backend chưa cung cấp API hoạt động gần đây.</p>
        <ol v-if="dashboard.activities?.length" class="mt-4 space-y-4">
          <li v-for="activity in dashboard.activities" :key="activity.id" class="flex gap-3">
            <span class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"><Send :size="15" aria-hidden="true" /></span>
            <div class="min-w-0">
              <p class="text-sm font-semibold text-navy">{{ activity.action }}</p>
              <p class="truncate text-xs text-muted">{{ activity.title }}<span v-if="activity.detail"> · {{ activity.detail }}</span></p>
              <p class="mt-1 text-[11px] text-muted">{{ formatDate(activity.createdAt) }}</p>
            </div>
          </li>
        </ol>
        <div v-else class="mt-4 rounded-xl border border-dashed border-slate-200 p-4 text-sm text-muted">Chưa có API cung cấp lịch sử hoạt động Provider.</div>
      </article>
    </section>
  </div>
</template>
