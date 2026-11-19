<script setup>
import { computed, ref } from 'vue'
import { BarChart3, BookOpen, Eye, FileText, GraduationCap, Users } from 'lucide-vue-next'
import { getAdminAnalytics } from '@/service/adminService'

const period = ref('30d')
const analytics = computed(() => getAdminAnalytics(period.value))
const maxApprovals = computed(() => Math.max(1, ...analytics.value.approvals))
const periodLabel = computed(() => ({
  '7d': '7 ngày gần nhất',
  '30d': '30 ngày gần nhất',
  '3m': '3 tháng gần nhất',
  '12m': '12 tháng gần nhất',
}[period.value]))
const cards = computed(() => [
  { label: 'Tài khoản', value: analytics.value.users, icon: Users },
  { label: 'Reviewer', value: analytics.value.reviewers, icon: GraduationCap },
  { label: 'Người cung cấp', value: analytics.value.providers, icon: Users },
  { label: 'Khóa học', value: analytics.value.courses, icon: BookOpen },
  { label: 'Bài học', value: analytics.value.lessons, icon: GraduationCap },
  { label: 'Tài liệu', value: analytics.value.materials, icon: FileText },
  { label: 'Lượt đăng ký', value: analytics.value.enrollments, icon: BarChart3 },
  { label: 'Đang hiển thị / Đã ẩn', value: `${analytics.value.visible} / ${analytics.value.hidden}`, icon: Eye },
])

function formatNumber(value) {
  return Number.isFinite(value) ? value.toLocaleString('vi-VN') : '—'
}
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Hệ thống</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Thống kê hệ thống</h2>
        <p class="mt-2 text-sm leading-6 text-muted">Tổng hợp tài khoản, nội dung, lượt đăng ký và kiểm duyệt theo khoảng thời gian.</p>
      </div>
      <label class="flex items-center gap-2 text-sm font-medium text-navy">
        <span>Khoảng thời gian</span>
        <select v-model="period" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="7d">7 ngày</option>
          <option value="30d">30 ngày</option>
          <option value="3m">3 tháng</option>
          <option value="12m">12 tháng</option>
        </select>
      </label>
    </section>

    <p class="rounded-xl border border-primary/15 bg-primary/5 p-3 text-sm text-navy" role="status">Các số liệu trên là dữ liệu mẫu tĩnh cho giao diện, không phải báo cáo từ cơ sở dữ liệu. Khoảng đang xem: <strong>{{ periodLabel }}</strong>.</p>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Thống kê tổng quan">
      <article v-for="card in cards" :key="card.label" class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div class="flex items-start justify-between gap-3">
          <p class="text-sm text-muted">{{ card.label }}</p>
          <span class="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary"><component :is="card.icon" :size="18" aria-hidden="true" /></span>
        </div>
        <p class="mt-4 text-2xl font-bold text-navy">{{ typeof card.value === 'number' ? formatNumber(card.value) : card.value }}</p>
      </article>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div>
        <h3 class="font-bold text-navy">Nội dung được phê duyệt</h3>
        <p class="mt-1 text-sm text-muted">Chỉ số minh họa theo {{ periodLabel.toLocaleLowerCase('vi') }}.</p>
      </div>
      <div class="mt-6 flex h-60 items-end justify-between gap-2 border-b border-slate-200 px-1 sm:gap-4 sm:px-3" role="img" aria-label="Biểu đồ số nội dung được phê duyệt">
        <div v-for="(count, index) in analytics.approvals" :key="`${period}-${index}`" class="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2">
          <span class="text-[11px] font-medium text-muted">{{ formatNumber(count) }}</span>
          <div class="flex h-full w-full items-end justify-center">
            <div class="w-full max-w-14 rounded-t-lg bg-primary/80" :style="{ height: `${Math.max(8, (count / maxApprovals) * 100)}%` }"></div>
          </div>
          <span class="pb-2 text-xs text-muted">Mốc {{ index + 1 }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
