<script setup>
import { computed } from 'vue'
import { Activity, BookOpen, FileText, Info, Sparkles, Users } from 'lucide-vue-next'
import { getRecommendationMetrics } from '@/service/adminService'

const metrics = computed(() => getRecommendationMetrics())
const maxCount = computed(() => Math.max(1, ...metrics.value.byDay.map((day) => day.value)))
const metricCards = computed(() => [
  { label: 'Lượt gợi ý', value: metrics.value.totalSuggestions, icon: Activity },
  { label: 'Người học tiếp cận', value: metrics.value.usersReached, icon: Users },
  { label: 'Khóa học được gợi ý', value: metrics.value.coursesSuggested, icon: BookOpen },
  { label: 'Tài liệu được gợi ý', value: metrics.value.materialsSuggested, icon: FileText },
])

function formatNumber(value) {
  return Number.isFinite(value) ? value.toLocaleString('vi-VN') : 'Chưa có dữ liệu'
}

function formatRate(value) {
  return Number.isFinite(value) ? `${value.toLocaleString('vi-VN')}%` : 'Chưa có dữ liệu'
}
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Hệ thống</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Hệ thống gợi ý AI</h2>
        <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">Theo dõi chỉ số gợi ý hiện có. Dữ liệu là mock, chưa kết nối mô hình hoặc API backend.</p>
      </div>
      <span class="inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent">
        <Sparkles :size="14" aria-hidden="true" /> {{ metrics.moduleStatus }}
      </span>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Chỉ số hệ thống gợi ý">
      <article v-for="card in metricCards" :key="card.label" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex items-start justify-between gap-3">
          <p class="text-sm text-muted">{{ card.label }}</p>
          <span class="flex size-9 items-center justify-center rounded-xl bg-accent/10 text-accent"><component :is="card.icon" :size="18" aria-hidden="true" /></span>
        </div>
        <p class="mt-4 text-2xl font-bold text-navy">{{ formatNumber(card.value) }}</p>
      </article>
    </section>

    <section class="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <header class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="font-bold text-navy">Lượt gợi ý theo ngày</h3>
            <p class="mt-1 text-sm text-muted">Biểu đồ dữ liệu minh họa, không phải báo cáo realtime.</p>
          </div>
          <span v-if="metrics.updatedAt" class="text-xs text-muted">Cập nhật {{ metrics.updatedAt }}</span>
        </header>
        <div class="mt-6 flex h-56 items-end justify-between gap-2 border-b border-slate-200 px-1 sm:gap-4 sm:px-3" role="img" aria-label="Biểu đồ lượt gợi ý theo ngày">
          <div v-for="day in metrics.byDay" :key="day.label" class="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2">
            <span class="text-[11px] font-medium text-muted">{{ formatNumber(day.value) }}</span>
            <div class="flex h-full w-full items-end justify-center">
              <div class="w-full max-w-12 rounded-t-lg bg-accent/80" :style="{ height: `${Math.max(8, (day.value / maxCount) * 100)}%` }"></div>
            </div>
            <span class="pb-2 text-xs text-muted">{{ day.label }}</span>
          </div>
        </div>
      </article>

      <aside class="space-y-4">
        <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 class="flex items-center gap-2 font-bold text-navy"><Activity :size="17" class="text-accent" aria-hidden="true" /> Tương tác gợi ý</h3>
          <dl class="mt-4 space-y-4">
            <div class="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <dt class="text-sm text-muted">Lượt nhấp</dt>
              <dd class="text-sm font-semibold text-navy">{{ formatNumber(metrics.clicks) }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3">
              <dt class="text-sm text-muted">Tỷ lệ tương tác</dt>
              <dd class="text-sm font-semibold text-navy">{{ formatRate(metrics.interactionRate) }}</dd>
            </div>
          </dl>
        </article>
        <div class="rounded-xl border border-accent/20 bg-accent/5 p-4 text-sm leading-6 text-navy">
          <p class="flex items-start gap-2 font-semibold"><Info :size="17" class="mt-0.5 shrink-0 text-accent" aria-hidden="true" /> Dữ liệu minh họa</p>
          <p class="mt-2 text-muted">Các chỉ số hiện được cung cấp từ mock data. Màn hình không tạo đề xuất, không thay đổi thuật toán và không khẳng định hiệu quả mô hình khi chưa có dữ liệu thực.</p>
        </div>
      </aside>
    </section>
  </div>
</template>
