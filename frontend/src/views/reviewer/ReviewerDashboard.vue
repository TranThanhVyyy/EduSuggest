<script setup>
import { computed } from 'vue'
import {
  ArrowUpRight,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  FileCheck2,
  Sparkles,
  XCircle,
} from 'lucide-vue-next'
import StatCard from '@/components/reviewer/StatCard.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getReviewerDashboardData } from '@/service/reviewerService'

const dashboard = computed(() => getReviewerDashboardData())
const statCards = computed(() => [
  {
    label: 'Khóa học chờ duyệt',
    value: dashboard.value.pendingCourses,
    detail: 'Bao gồm nội dung đang xem xét',
    icon: BookOpenCheck,
    tone: 'primary',
  },
  {
    label: 'Tài liệu chờ duyệt',
    value: dashboard.value.pendingMaterials,
    detail: 'Cần được kiểm tra',
    icon: FileCheck2,
    tone: 'accent',
  },
  {
    label: 'Nội dung đã phê duyệt',
    value: dashboard.value.approved,
    detail: 'Trong lịch sử kiểm duyệt',
    icon: CheckCircle2,
    tone: 'accent',
  },
  {
    label: 'Nội dung bị từ chối',
    value: dashboard.value.rejected,
    detail: 'Trong lịch sử kiểm duyệt',
    icon: XCircle,
    tone: 'navy',
  },
])

const maxReviews = computed(() =>
  Math.max(1, ...dashboard.value.weeklyStats.map((day) => day.reviewed)),
)

function detailRoute(item) {
  return item.itemType === 'course'
    ? { name: 'reviewer-course-detail', params: { id: item.id } }
    : { name: 'reviewer-material-detail', params: { id: item.id } }
}

function formatDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(new Date(value))
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Tổng quan</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Chào mừng đến không gian kiểm duyệt</h2>
        <p class="mt-2 text-sm text-muted">Theo dõi nội dung chờ xử lý và kết quả kiểm duyệt gần đây.</p>
      </div>
      <span class="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-muted">Dữ liệu minh họa trong phiên</span>
    </section>

    <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Thống kê kiểm duyệt">
      <StatCard
        v-for="card in statCards"
        :key="card.label"
        :label="card.label"
        :value="card.value"
        :detail="card.detail"
        :icon="card.icon"
        :tone="card.tone"
      />
    </section>

    <section class="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="font-bold text-navy">Kết quả kiểm duyệt trong tuần</h3>
            <p class="mt-1 text-sm text-muted">Số nội dung đã xử lý theo ngày</p>
          </div>
          <span class="inline-flex items-center gap-1.5 text-xs text-muted">
            <span class="size-2 rounded-full bg-primary"></span> Đã xử lý
          </span>
        </div>
        <div class="mt-7 flex h-48 items-end justify-between gap-2 border-b border-slate-200 px-1 sm:gap-4 sm:px-3">
          <div v-for="day in dashboard.weeklyStats" :key="day.label" class="flex h-full flex-1 flex-col items-center justify-end gap-2">
            <span class="text-[11px] font-medium text-muted">{{ day.reviewed }}</span>
            <div class="flex h-full w-full items-end justify-center">
              <div
                class="w-full max-w-10 rounded-t-lg bg-primary/80 transition hover:bg-primary"
                :style="{ height: `${Math.max(14, (day.reviewed / maxReviews) * 100)}%` }"
                :aria-label="`${day.label}: ${day.reviewed} nội dung`"
                role="img"
              ></div>
            </div>
            <span class="pb-2 text-xs text-muted">{{ day.label }}</span>
          </div>
        </div>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="font-bold text-navy">Truy cập nhanh</h3>
            <p class="mt-1 text-sm text-muted">Mở danh sách cần xử lý</p>
          </div>
          <Sparkles class="text-accent" :size="19" aria-hidden="true" />
        </div>
        <div class="mt-5 grid gap-3">
          <RouterLink :to="{ name: 'reviewer-courses' }" class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-4 transition hover:border-primary/40 hover:bg-background focus-visible:outline-2 focus-visible:outline-primary">
            <span class="flex items-center gap-3">
              <span class="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><BookOpenCheck :size="18" aria-hidden="true" /></span>
              <span>
                <span class="block text-sm font-semibold text-navy">Khóa học chờ duyệt</span>
                <span class="mt-1 block text-xs text-muted">{{ dashboard.pendingCourses }} nội dung</span>
              </span>
            </span>
            <ArrowUpRight class="text-muted" :size="17" aria-hidden="true" />
          </RouterLink>
          <RouterLink :to="{ name: 'reviewer-materials' }" class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-4 transition hover:border-primary/40 hover:bg-background focus-visible:outline-2 focus-visible:outline-primary">
            <span class="flex items-center gap-3">
              <span class="flex size-10 items-center justify-center rounded-xl bg-accent/10 text-accent"><FileCheck2 :size="18" aria-hidden="true" /></span>
              <span>
                <span class="block text-sm font-semibold text-navy">Tài liệu chờ duyệt</span>
                <span class="mt-1 block text-xs text-muted">{{ dashboard.pendingMaterials }} nội dung</span>
              </span>
            </span>
            <ArrowUpRight class="text-muted" :size="17" aria-hidden="true" />
          </RouterLink>
        </div>
      </article>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
        <div>
          <h3 class="font-bold text-navy">Yêu cầu kiểm duyệt mới nhất</h3>
          <p class="mt-1 text-sm text-muted">Nội dung đang chờ hoặc được xem xét</p>
        </div>
        <RouterLink :to="{ name: 'reviewer-history' }" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
          Lịch sử kiểm duyệt <ArrowUpRight :size="16" aria-hidden="true" />
        </RouterLink>
      </div>
      <div v-if="dashboard.recentItems.length" class="divide-y divide-slate-100">
        <RouterLink
          v-for="item in dashboard.recentItems"
          :key="`${item.itemType}-${item.id}`"
          :to="detailRoute(item)"
          class="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition hover:bg-background/70"
        >
          <span class="flex min-w-0 items-center gap-3">
            <span class="flex size-10 shrink-0 items-center justify-center rounded-xl" :class="item.itemType === 'course' ? 'bg-primary/10 text-primary' : 'bg-accent/10 text-accent'">
              <BookOpenCheck v-if="item.itemType === 'course'" :size="18" aria-hidden="true" />
              <FileCheck2 v-else :size="18" aria-hidden="true" />
            </span>
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-navy">{{ item.title }}</span>
              <span class="mt-1 block text-xs text-muted">{{ item.creator }} · {{ formatDate(item.submittedAt) }}</span>
            </span>
          </span>
          <span class="flex items-center gap-3">
            <StatusBadge :status="item.status" />
            <Clock3 class="hidden text-muted sm:block" :size="16" aria-hidden="true" />
          </span>
        </RouterLink>
      </div>
      <p v-else class="p-6 text-center text-sm text-muted">Hiện không có nội dung cần xử lý.</p>
    </section>
  </div>
</template>
