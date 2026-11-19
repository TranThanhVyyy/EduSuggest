<script setup>
import { computed } from 'vue'
import {
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Eye,
  FileText,
  GraduationCap,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-vue-next'
import { getAdminDashboardStats, getAdminReviewRequests, getRecommendationMetrics } from '@/service/adminService'

const stats = computed(() => getAdminDashboardStats())
const recommendations = computed(() => getRecommendationMetrics())
const reviewRequests = computed(() => getAdminReviewRequests().slice(0, 5))
const maxRecommendationCount = computed(() => Math.max(1, ...recommendations.value.byDay.map((day) => day.value)))

const statCards = computed(() => [
  { label: 'Tổng tài khoản', value: stats.value.users, icon: Users, tone: 'primary', to: 'admin-users' },
  { label: 'Chuyên gia Reviewer', value: stats.value.reviewers, icon: ShieldCheck, tone: 'accent', to: 'admin-reviewers' },
  { label: 'Khóa học đã duyệt', value: stats.value.approvedCourses, icon: BookOpen, tone: 'primary', to: 'admin-courses' },
  { label: 'Bài học đã duyệt', value: stats.value.lessons, icon: GraduationCap, tone: 'navy', to: 'admin-courses' },
  { label: 'Tài liệu đã duyệt', value: stats.value.materials, icon: FileText, tone: 'accent', to: 'admin-materials' },
  { label: 'Lượt đăng ký', value: stats.value.enrollments.toLocaleString('vi-VN'), icon: Users, tone: 'primary', to: 'admin-analytics' },
  { label: 'Nội dung đang hiển thị', value: stats.value.visible, icon: Eye, tone: 'accent', to: 'admin-visibility' },
  { label: 'Nội dung đã ẩn', value: stats.value.hidden, icon: Eye, tone: 'navy', to: 'admin-visibility' },
])

const quickLinks = computed(() => [
  { label: 'Tài khoản', description: 'Quản lý tài khoản và chuyên gia', routeName: 'admin-users', icon: Users },
  { label: 'Nội dung đã duyệt', description: 'Khóa học, bài học và tài liệu', routeName: 'admin-courses', icon: BookOpen },
  { label: 'Phân công Reviewer', description: `${stats.value.unassigned} yêu cầu chưa phân công`, routeName: 'admin-assign-reviewer', icon: ShieldCheck },
  { label: 'Thống kê hệ thống', description: 'Tổng quan và xu hướng', routeName: 'admin-analytics', icon: BarChart3 },
])

function formatDate(value) {
  if (!value) return 'Chưa có ngày gửi'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có ngày gửi' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
</script>

<template>
  <div class="space-y-6">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Tổng quan hệ thống</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Chào mừng đến Trung tâm quản trị</h2>
        <p class="mt-2 text-sm text-muted">Theo dõi hoạt động, nội dung đã duyệt và tiến độ kiểm duyệt.</p>
      </div>
      <span class="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-muted">Dữ liệu minh họa · Chưa kết nối API</span>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Thống kê hệ thống">
      <RouterLink v-for="card in statCards" :key="card.label" :to="{ name: card.to }" class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md sm:p-5">
        <div class="flex items-start justify-between gap-2">
          <p class="text-sm font-medium text-muted">{{ card.label }}</p>
          <span class="flex size-9 shrink-0 items-center justify-center rounded-xl" :class="card.tone === 'accent' ? 'bg-accent/10 text-accent' : card.tone === 'navy' ? 'bg-navy/5 text-navy' : 'bg-primary/10 text-primary'">
            <component :is="card.icon" :size="18" aria-hidden="true" />
          </span>
        </div>
        <p class="mt-4 text-2xl font-bold tracking-tight text-navy">{{ card.value }}</p>
        <span class="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary">Xem chi tiết <ArrowUpRight :size="14" aria-hidden="true" /></span>
      </RouterLink>
    </section>

    <section class="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.85fr)]">
      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="font-bold text-navy">Hoạt động hệ thống gợi ý</h3>
            <p class="mt-1 text-sm text-muted">Lượt gợi ý theo ngày · dữ liệu mẫu</p>
          </div>
          <span class="inline-flex items-center gap-1.5 text-xs text-muted"><span class="size-2 rounded-full bg-accent"></span> {{ recommendations.moduleStatus }}</span>
        </div>
        <div class="mt-6 flex h-48 items-end justify-between gap-2 border-b border-slate-200 px-1 sm:gap-4 sm:px-3">
          <div v-for="day in recommendations.byDay" :key="day.label" class="flex h-full flex-1 flex-col items-center justify-end gap-2">
            <span class="text-[11px] font-medium text-muted">{{ day.value }}</span>
            <div class="flex h-full w-full items-end justify-center">
              <div class="w-full max-w-10 rounded-t-lg bg-accent/80" :style="{ height: `${Math.max(12, (day.value / maxRecommendationCount) * 100)}%` }"></div>
            </div>
            <span class="pb-2 text-xs text-muted">{{ day.label }}</span>
          </div>
        </div>
        <RouterLink :to="{ name: 'admin-recommendations' }" class="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
          Xem hệ thống gợi ý <ArrowUpRight :size="15" aria-hidden="true" />
        </RouterLink>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="font-bold text-navy">Truy cập nhanh</h3>
            <p class="mt-1 text-sm text-muted">Quản trị và giám sát</p>
          </div>
          <Sparkles class="text-accent" :size="20" aria-hidden="true" />
        </div>
        <div class="mt-4 grid gap-2">
          <RouterLink v-for="link in quickLinks" :key="link.routeName" :to="{ name: link.routeName }" class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 transition hover:border-primary/40 hover:bg-background">
            <span class="flex min-w-0 items-center gap-3">
              <span class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><component :is="link.icon" :size="17" aria-hidden="true" /></span>
              <span class="min-w-0">
                <span class="block truncate text-sm font-semibold text-navy">{{ link.label }}</span>
                <span class="mt-0.5 block truncate text-xs text-muted">{{ link.description }}</span>
              </span>
            </span>
            <ArrowUpRight class="shrink-0 text-muted" :size="16" aria-hidden="true" />
          </RouterLink>
        </div>
      </article>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
        <div>
          <h3 class="font-bold text-navy">Theo dõi yêu cầu kiểm duyệt</h3>
          <p class="mt-1 text-sm text-muted">Admin giám sát tiến độ, Reviewer là người quyết định.</p>
        </div>
        <RouterLink :to="{ name: 'admin-review-monitor' }" class="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
          Mở theo dõi <ArrowUpRight :size="15" aria-hidden="true" />
        </RouterLink>
      </header>
      <div v-if="reviewRequests.length" class="divide-y divide-slate-100">
        <div v-for="item in reviewRequests" :key="`${item.itemType}-${item.id}`" class="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
          <span class="min-w-0">
            <span class="block truncate text-sm font-semibold text-navy">{{ item.title }}</span>
            <span class="mt-1 block text-xs text-muted">{{ item.itemType === 'course' ? 'Khóa học' : 'Tài liệu' }} · {{ item.creator }} · {{ formatDate(item.submittedAt) }}</span>
          </span>
          <span class="flex items-center gap-3">
            <span class="rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-muted">{{ item.status === 'DangKiemDuyet' ? 'Đang kiểm duyệt' : item.status === 'YeuCauChinhSua' ? 'Yêu cầu chỉnh sửa' : 'Chờ kiểm duyệt' }}</span>
            <RouterLink :to="{ name: 'admin-review-monitor' }" class="text-xs font-semibold text-primary hover:underline">Theo dõi</RouterLink>
          </span>
        </div>
      </div>
      <p v-else class="p-6 text-center text-sm text-muted">Không có yêu cầu đang chờ theo dõi.</p>
    </section>
  </div>
</template>
