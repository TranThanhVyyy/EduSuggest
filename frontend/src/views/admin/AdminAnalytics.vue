<script setup>
import { onMounted, ref } from 'vue'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FileText,
  GraduationCap,
  RefreshCw,
  TrendingUp,
  Users,
} from 'lucide-vue-next'
import api from '@/service/api'

const summary = ref(null)
const loading = ref(false)
const errorMessage = ref('')

async function fetchSummary() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.get('/admin/analytics/summary')
    summary.value = data
  } catch (error) {
    errorMessage.value =
      error.response?.data?.detail || 'Không thể tải dữ liệu thống kê từ máy chủ.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSummary()
})
</script>

<template>
  <main class="space-y-6">
    <header class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-5">
      <div>
        <p class="ui-eyebrow">Điều hành EduSuggest</p>
        <h1 class="ui-page-title mt-2">Thống kê hệ thống</h1>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-navy shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
        :disabled="loading"
        @click="fetchSummary"
      >
        <RefreshCw :size="16" :class="{ 'animate-spin': loading }" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <!-- Error State -->
    <div
      v-if="errorMessage"
      class="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
      role="alert"
    >
      <AlertCircle :size="18" class="mt-0.5 shrink-0 text-red-600" aria-hidden="true" />
      <div class="flex-1">
        <p class="font-medium">Đã xảy ra lỗi khi tải thống kê</p>
        <p class="mt-1 text-red-700">{{ errorMessage }}</p>
        <button
          type="button"
          class="mt-2 font-medium text-red-800 underline hover:text-red-900"
          @click="fetchSummary"
        >
          Thử lại
        </button>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <section v-if="loading && !summary" aria-label="Đang tải dữ liệu" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div
        v-for="i in 4"
        :key="i"
        class="animate-pulse rounded-2xl border border-border bg-white p-5 shadow-sm space-y-3"
      >
        <div class="size-10 rounded-xl bg-slate-100"></div>
        <div class="h-4 w-24 rounded bg-slate-100"></div>
        <div class="h-8 w-16 rounded bg-slate-100"></div>
      </div>
    </section>

    <!-- Content -->
    <div v-else-if="summary" class="space-y-6">
      <!-- 4 Core Metric Cards -->
      <section aria-label="Các chỉ số chính" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <!-- Tổng người dùng -->
        <article class="rounded-2xl border border-border bg-white p-5 shadow-sm hover:border-primary/20 transition-colors">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted">Người dùng</span>
            <span class="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
              <Users :size="20" aria-hidden="true" />
            </span>
          </div>
          <p class="mt-3 text-3xl font-bold tracking-tight text-navy">
            {{ summary.total_users.toLocaleString('vi-VN') }}
          </p>
          <p class="mt-1 text-xs text-muted">Tổng số tài khoản trong hệ thống</p>
        </article>

        <!-- Tổng khóa học -->
        <article class="rounded-2xl border border-border bg-white p-5 shadow-sm hover:border-primary/20 transition-colors">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted">Khóa học</span>
            <span class="flex size-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <BookOpen :size="20" aria-hidden="true" />
            </span>
          </div>
          <p class="mt-3 text-3xl font-bold tracking-tight text-navy">
            {{ summary.total_courses.toLocaleString('vi-VN') }}
          </p>
          <p class="mt-1 text-xs text-muted">Tổng số khóa học đã khởi tạo</p>
        </article>

        <!-- Tổng bài học -->
        <article class="rounded-2xl border border-border bg-white p-5 shadow-sm hover:border-primary/20 transition-colors">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted">Bài học</span>
            <span class="flex size-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <FileText :size="20" aria-hidden="true" />
            </span>
          </div>
          <p class="mt-3 text-3xl font-bold tracking-tight text-navy">
            {{ summary.total_lessons.toLocaleString('vi-VN') }}
          </p>
          <p class="mt-1 text-xs text-muted">Nội dung bài giảng và thực hành</p>
        </article>

        <!-- Tỷ lệ hoàn thành -->
        <article class="rounded-2xl border border-border bg-white p-5 shadow-sm hover:border-primary/20 transition-colors">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-muted">Tỷ lệ hoàn thành</span>
            <span class="flex size-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
              <TrendingUp :size="20" aria-hidden="true" />
            </span>
          </div>
          <p class="mt-3 text-3xl font-bold tracking-tight text-navy">
            {{ summary.completion_rate }}%
          </p>
          <p class="mt-1 text-xs text-muted">Tỷ lệ hoàn thành khóa học</p>
        </article>
      </section>

      <!-- Detailed Enrollment Stats -->
      <section aria-label="Chi tiết lượt học" class="rounded-2xl border border-border bg-white p-6 shadow-sm">
        <div class="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h2 class="text-base font-semibold text-navy">Tiến độ và lượt đăng ký học</h2>
            <p class="text-xs text-muted mt-0.5">Thống kê tương tác học tập của học viên</p>
          </div>
          <span class="flex size-9 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
            <GraduationCap :size="18" aria-hidden="true" />
          </span>
        </div>

        <div class="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div class="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
            <p class="text-xs font-medium text-muted">Tổng lượt đăng ký</p>
            <p class="mt-2 text-2xl font-bold text-navy">
              {{ summary.total_enrollments.toLocaleString('vi-VN') }}
            </p>
            <p class="mt-1 text-xs text-muted">Tổng số lượt người học ghi danh</p>
          </div>

          <div class="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
            <div class="flex items-center gap-1.5">
              <CheckCircle2 :size="14" class="text-emerald-600" aria-hidden="true" />
              <p class="text-xs font-medium text-muted">Đã hoàn thành</p>
            </div>
            <p class="mt-2 text-2xl font-bold text-emerald-700">
              {{ summary.completed_enrollments.toLocaleString('vi-VN') }}
            </p>
            <p class="mt-1 text-xs text-muted">Lượt học đạt 100% hoặc có ngày kết thúc</p>
          </div>

          <div class="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
            <p class="text-xs font-medium text-muted">Hiệu suất đào tạo</p>
            <div class="mt-2 flex items-baseline gap-2">
              <span class="text-2xl font-bold text-navy">{{ summary.completion_rate }}%</span>
              <span class="text-xs text-muted">
                ({{ summary.completed_enrollments }}/{{ summary.total_enrollments || 1 }})
              </span>
            </div>
            <!-- Progress Bar -->
            <div class="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                class="h-full rounded-full bg-primary transition-all duration-500"
                :style="{ width: `${Math.min(summary.completion_rate, 100)}%` }"
              ></div>
            </div>
          </div>
        </div>
      </section>

      <!-- Empty State if no data in DB -->
      <section
        v-if="summary.total_users === 0 && summary.total_courses === 0"
        class="border-l-2 border-accent py-2 pl-4"
        role="status"
      >
        <h3 class="font-medium text-navy">Chưa có dữ liệu vận hành</h3>
        <p class="mt-1 text-sm text-muted">Hệ thống chưa có khóa học và tài khoản người dùng hoạt động.</p>
      </section>
    </div>
  </main>
</template>
