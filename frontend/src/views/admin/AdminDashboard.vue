<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BarChart3,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Eye,
  GraduationCap,
  RefreshCw,
  Sparkles,
  Tags,
  UserCog,
  Users,
} from 'lucide-vue-next'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import { authState } from '@/service/authState'
import api from '@/service/api'

const summary = ref(null)
const usersList = ref([])
const coursesList = ref([])
const categoriesList = ref([])
const loading = ref(true)
const errorMessage = ref('')

const adminShortName = computed(() => {
  const full = authState.user?.hoTen?.trim()
  if (!full) return ''
  const parts = full.split(/\s+/)
  return parts[parts.length - 1] || full
})

const ledgerItems = computed(() => {
  const s = summary.value
  return [
    {
      key: 'users',
      label: 'Người dùng',
      value: s ? s.total_users.toLocaleString('vi-VN') : '—',
      sub: 'Tài khoản hệ thống',
      dotClass: 'bg-navy',
      to: { name: 'admin-users' },
    },
    {
      key: 'courses',
      label: 'Khóa học',
      value: s ? s.total_courses.toLocaleString('vi-VN') : '—',
      sub: 'Toàn bộ danh mục',
      dotClass: 'bg-teal',
      to: { name: 'admin-courses' },
    },
    {
      key: 'enrollments',
      label: 'Lượt ghi danh',
      value: s ? s.total_enrollments.toLocaleString('vi-VN') : '—',
      sub: 'Đăng ký học tập',
      dotClass: 'bg-amber',
      to: { name: 'admin-analytics' },
    },
    {
      key: 'completion',
      label: 'Tỷ lệ hoàn thành',
      value: s ? `${s.completion_rate}%` : '—',
      sub: s ? `${s.completed_enrollments}/${s.total_enrollments} lượt` : 'Hiệu suất học',
      dotClass: 'bg-emerald-500',
      to: { name: 'admin-analytics' },
    },
  ]
})

// Chart 1: Real User Distribution by Role (SVG Donut)
const roleSegments = computed(() => {
  const total = usersList.value.length
  const defs = [
    { role: 'USER', label: 'Người học', color: '#0D9488', dotClass: 'bg-teal', route: 'admin-users' },
    { role: 'PROVIDER', label: 'Nhà cung cấp', color: '#D97706', dotClass: 'bg-amber', route: 'admin-providers' },
    { role: 'EXPERT', label: 'Chuyên gia', color: '#112233', dotClass: 'bg-navy', route: 'admin-reviewers' },
    { role: 'ADMIN', label: 'Quản trị', color: '#94A3B8', dotClass: 'bg-slate-400', route: 'admin-dashboard' },
  ]
  const circumference = 2 * Math.PI * 52
  let cumulative = 0
  return defs.map((def) => {
    const count = usersList.value.filter((u) => u.tenVaiTro === def.role).length
    const ratio = total > 0 ? count / total : 0
    const length = ratio * circumference
    const offset = -cumulative
    cumulative += length
    return {
      ...def,
      count,
      percent: total > 0 ? Math.round(ratio * 100) : 0,
      dasharray: `${length} ${circumference}`,
      dashoffset: offset,
    }
  })
})

// Chart 2: Real Course Distribution by Category (Horizontal Bar Chart)
const categoryBars = computed(() => {
  const nameById = new Map(categoriesList.value.map((c) => [String(c.maDanhMuc), c.tenDanhMuc]))
  const countMap = new Map()
  for (const course of coursesList.value) {
    const key = course.maDanhMuc != null ? String(course.maDanhMuc) : 'none'
    countMap.set(key, (countMap.get(key) || 0) + 1)
  }
  const items = Array.from(countMap.entries())
    .map(([key, count]) => ({
      id: key,
      name: key === 'none' ? 'Chưa phân loại' : (nameById.get(key) || `Danh mục #${key}`),
      count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
  const max = items[0]?.count || 1
  return items.map((item) => ({
    ...item,
    widthPercent: Math.max(8, Math.round((item.count / max) * 100)),
  }))
})

const courseStatusBreakdown = computed(() => {
  const list = coursesList.value
  return [
    { label: 'Đã duyệt', count: list.filter((c) => c.trangThaiDuyet === 'APPROVED').length, dotClass: 'bg-teal' },
    { label: 'Chờ duyệt', count: list.filter((c) => c.trangThaiDuyet === 'PENDING').length, dotClass: 'bg-amber' },
    { label: 'Bản nháp', count: list.filter((c) => !c.trangThaiDuyet || c.trangThaiDuyet === 'DRAFT').length, dotClass: 'bg-slate-400' },
    {
      label: 'Cần sửa / Từ chối',
      count: list.filter((c) => ['REJECTED', 'NEEDS_REVISION'].includes(c.trangThaiDuyet)).length,
      dotClass: 'bg-rose-500',
    },
  ]
})

const coreOperations = [
  {
    title: 'Duyệt hồ sơ nhà cung cấp',
    description: 'Xét duyệt yêu cầu nâng cấp tài khoản đối tác đào tạo mới.',
    route: 'admin-provider-applications',
    icon: ClipboardList,
    highlight: 'Ưu tiên',
  },
  {
    title: 'Quản lý tài khoản người học',
    description: 'Tra cứu tài khoản USER, cấp quyền Chuyên gia, khóa hoặc xóa tài khoản.',
    route: 'admin-users',
    icon: Users,
  },
  {
    title: 'Danh mục khóa học',
    description: 'Tạo mới, chỉnh sửa và chuẩn hóa nhóm ngành đào tạo.',
    route: 'admin-categories',
    icon: Tags,
  },
  {
    title: 'Kiểm soát hiển thị công khai',
    description: 'Bật/tắt hiển thị các khóa học và tài liệu đã qua kiểm duyệt.',
    route: 'admin-visibility',
    icon: Eye,
  },
]

const systemAreas = [
  { title: 'Đội ngũ chuyên gia', subtitle: 'Cấp lại mật khẩu, khóa & quản lý chuyên gia', route: 'admin-reviewers', icon: UserCog },
  { title: 'Nhà cung cấp đào tạo', subtitle: 'Quản lý đối tác xuất bản nội dung', route: 'admin-providers', icon: GraduationCap },
  { title: 'Theo dõi kiểm duyệt', subtitle: 'Giám sát hàng đợi & phản hồi', route: 'admin-review-monitor', icon: ClipboardCheck },
  { title: 'Hệ thống gợi ý', subtitle: 'Cấu hình & vận hành gợi ý học tập', route: 'admin-recommendations', icon: Sparkles },
]

async function fetchSummary() {
  loading.value = true
  errorMessage.value = ''
  const [summaryRes, usersRes, coursesRes, categoriesRes] = await Promise.allSettled([
    api.get('/admin/analytics/summary'),
    api.get('/admin/users'),
    api.get('/admin/courses'),
    api.get('/admin/categories'),
  ])

  if (summaryRes.status === 'fulfilled') {
    summary.value = summaryRes.value.data
  } else {
    errorMessage.value =
      summaryRes.reason?.response?.data?.detail || 'Không thể tải dữ liệu thống kê từ máy chủ.'
  }

  if (usersRes.status === 'fulfilled') usersList.value = usersRes.value.data || []
  if (coursesRes.status === 'fulfilled') coursesList.value = coursesRes.value.data || []
  if (categoriesRes.status === 'fulfilled') categoriesList.value = categoriesRes.value.data || []

  loading.value = false
}

onMounted(fetchSummary)
</script>

<template>
  <div class="space-y-8">
    <!-- Editorial Page Header -->
    <section class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1">
        <h1 class="font-display text-2xl font-bold tracking-tight text-navy sm:text-[28px]">
          {{ adminShortName ? `Xin chào, ${adminShortName}` : 'Trung tâm quản trị' }}
        </h1>
        <p class="text-sm text-slate-600">
          Tổng quan vận hành hệ thống, phân bổ người dùng và kiểm soát chất lượng đào tạo.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 shrink-0">
        <RouterLink
          :to="{ name: 'admin-analytics' }"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
        >
          <BarChart3 :size="15" class="text-teal" aria-hidden="true" />
          <span>Báo cáo chi tiết</span>
        </RouterLink>

        <button
          type="button"
          class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
          :disabled="loading"
          @click="fetchSummary"
        >
          <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
      </div>
    </section>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể tải dữ liệu thống kê"
      :message="errorMessage"
    />

    <!-- Structured Operations Ledger -->
    <section
      aria-label="Chỉ số vận hành hệ thống"
      class="overflow-hidden rounded-2xl border border-border bg-surface"
    >
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 px-5 py-3">
        <div class="flex items-center gap-2.5">
          <span class="text-xs font-semibold text-navy">Chỉ số vận hành</span>
          <span class="text-xs text-slate-400" aria-hidden="true">·</span>
          <span class="text-xs text-slate-500 tabular-nums">
            {{ loading ? 'Đang tải…' : (summary ? `${summary.completed_enrollments}/${summary.total_enrollments} lượt hoàn thành` : 'Chưa có dữ liệu') }}
          </span>
        </div>

        <div v-if="summary" class="flex items-center gap-2" aria-label="Tiến độ hoàn thành trung bình">
          <div class="h-1.5 w-32 overflow-hidden rounded-full bg-subtle">
            <div
              class="h-full rounded-full bg-teal transition-[width] duration-300"
              :style="{ width: `${Math.min(summary.completion_rate, 100)}%` }"
            ></div>
          </div>
          <span class="text-xs font-semibold text-teal-dark tabular-nums">{{ summary.completion_rate }}%</span>
        </div>
      </div>

      <div v-if="loading && !summary" class="grid grid-cols-2 gap-3 p-5 sm:grid-cols-4">
        <UiSkeleton v-for="i in 4" :key="i" variant="rect" height="68px" rounded="0.75rem" />
      </div>

      <div v-else class="grid grid-cols-2 divide-y divide-border/70 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <RouterLink
          v-for="item in ledgerItems"
          :key="item.key"
          :to="item.to"
          class="group flex flex-col justify-between px-5 py-4 transition-colors duration-150 hover:bg-background/80 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-teal"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="flex items-center gap-2 text-xs font-medium text-slate-500 group-hover:text-navy">
              <span class="size-1.5 shrink-0 rounded-full" :class="item.dotClass" aria-hidden="true"></span>
              <span class="truncate">{{ item.label }}</span>
            </span>
            <ChevronRight
              :size="14"
              class="shrink-0 text-slate-400 opacity-0 transition-[opacity,transform] duration-150 group-hover:translate-x-0.5 group-hover:opacity-100"
              aria-hidden="true"
            />
          </div>

          <div class="mt-3 flex items-baseline justify-between gap-2">
            <span class="font-display text-[28px] font-semibold leading-none tracking-tight text-navy tabular-nums">
              {{ item.value }}
            </span>
            <span class="truncate text-[11px] font-medium text-slate-400 tabular-nums">
              {{ item.sub }}
            </span>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- Real-Data Charts Row -->
    <section aria-label="Biểu đồ phân tích hệ thống" class="grid gap-6 lg:grid-cols-12 items-stretch">
      <!-- Chart 1: Donut Chart of Users by Role -->
      <article class="flex flex-col justify-between rounded-2xl border border-border bg-surface p-5 sm:p-6 lg:col-span-5">
        <div class="flex items-center justify-between gap-2">
          <div>
            <h2 class="text-sm font-bold text-navy">Phân bổ tài khoản</h2>
            <p class="mt-0.5 text-xs text-slate-500">Tỷ trọng theo từng nhóm vai trò</p>
          </div>
          <span class="text-xs font-semibold text-slate-500 tabular-nums">
            {{ usersList.length }} tài khoản
          </span>
        </div>

        <div v-if="loading" class="my-6">
          <UiSkeleton variant="rect" height="160px" rounded="0.75rem" />
        </div>

        <div v-else class="mt-5 flex flex-col items-center gap-5 sm:flex-row">
          <div class="relative size-36 shrink-0">
            <svg viewBox="0 0 140 140" class="size-full -rotate-90" role="img" aria-label="Biểu đồ phân bổ tài khoản theo vai trò">
              <circle cx="70" cy="70" r="52" fill="none" stroke="#F1F5F4" stroke-width="16" />
              <circle
                v-for="seg in roleSegments"
                :key="seg.role"
                cx="70"
                cy="70"
                r="52"
                fill="none"
                :stroke="seg.color"
                stroke-width="16"
                :stroke-dasharray="seg.dasharray"
                :stroke-dashoffset="seg.dashoffset"
              />
            </svg>
            <div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <span class="text-2xl font-bold leading-none text-navy tabular-nums">{{ usersList.length }}</span>
              <span class="mt-1 text-[11px] text-slate-500">Tài khoản</span>
            </div>
          </div>

          <ul class="w-full flex-1 space-y-2.5 text-xs">
            <li v-for="seg in roleSegments" :key="`legend-${seg.role}`">
              <RouterLink
                :to="{ name: seg.route }"
                class="flex items-center justify-between gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-subtle/70"
              >
                <span class="flex items-center gap-2 font-medium text-slate-700">
                  <span class="size-2 shrink-0 rounded-full" :class="seg.dotClass" aria-hidden="true"></span>
                  <span>{{ seg.label }}</span>
                </span>
                <span class="font-semibold text-navy tabular-nums">
                  {{ seg.count }} <span class="font-normal text-slate-400">({{ seg.percent }}%)</span>
                </span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </article>

      <!-- Chart 2: Horizontal Bar Chart of Courses by Category -->
      <article class="flex flex-col justify-between rounded-2xl border border-border bg-surface p-5 sm:p-6 lg:col-span-7">
        <div class="flex items-center justify-between gap-2">
          <div>
            <h2 class="text-sm font-bold text-navy">Khóa học theo danh mục</h2>
            <p class="mt-0.5 text-xs text-slate-500">Top danh mục có nhiều khóa học nhất trên hệ thống</p>
          </div>
          <span class="text-xs font-semibold text-slate-500 tabular-nums">
            {{ coursesList.length }} khóa học
          </span>
        </div>

        <div v-if="loading" class="my-6 space-y-3">
          <UiSkeleton v-for="i in 4" :key="i" variant="rect" height="22px" rounded="0.5rem" />
        </div>

        <div v-else-if="categoryBars.length" class="mt-5 space-y-3">
          <div v-for="bar in categoryBars" :key="bar.id" class="space-y-1">
            <div class="flex items-center justify-between gap-3 text-xs">
              <span class="truncate font-medium text-slate-700">{{ bar.name }}</span>
              <span class="shrink-0 font-semibold text-navy tabular-nums">{{ bar.count }}</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
              <div
                class="h-full rounded-full bg-teal transition-[width] duration-300"
                :style="{ width: `${bar.widthPercent}%` }"
              ></div>
            </div>
          </div>
        </div>

        <p v-else class="py-8 text-center text-xs text-slate-500">Chưa có dữ liệu khóa học.</p>

        <!-- Course Approval Breakdown Footer -->
        <div class="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/70 pt-3.5 text-xs">
          <span
            v-for="st in courseStatusBreakdown"
            :key="st.label"
            class="inline-flex items-center gap-1.5 text-slate-600"
          >
            <span class="size-1.5 rounded-full" :class="st.dotClass" aria-hidden="true"></span>
            <span>{{ st.label }}:</span>
            <strong class="font-semibold text-navy tabular-nums">{{ st.count }}</strong>
          </span>
        </div>
      </article>
    </section>

    <!-- 2-Column Executive Operations Workspace -->
    <div class="grid gap-6 lg:grid-cols-12 items-start">
      <!-- Left: Core Operations List -->
      <section class="overflow-hidden rounded-2xl border border-border bg-surface lg:col-span-7">
        <div class="border-b border-border/70 px-5 py-3.5">
          <h2 class="text-sm font-bold text-navy">Tác vụ điều hành chính</h2>
        </div>

        <ul class="divide-y divide-border/70">
          <li v-for="op in coreOperations" :key="op.route">
            <RouterLink
              :to="{ name: op.route }"
              class="group flex items-center justify-between gap-4 px-5 py-4 transition-colors duration-150 hover:bg-background/70 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-teal"
            >
              <div class="flex min-w-0 items-start gap-3.5">
                <span class="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl border border-border bg-subtle/70 text-slate-600 transition-colors duration-150 group-hover:border-teal/40 group-hover:text-teal">
                  <component :is="op.icon" :size="17" aria-hidden="true" />
                </span>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-semibold text-navy transition-colors duration-150 group-hover:text-teal">
                      {{ op.title }}
                    </span>
                    <span
                      v-if="op.highlight"
                      class="rounded-full bg-amber/15 px-2 py-0.5 text-[10px] font-semibold text-amber"
                    >
                      {{ op.highlight }}
                    </span>
                  </div>
                  <p class="mt-0.5 text-xs text-slate-500">
                    {{ op.description }}
                  </p>
                </div>
              </div>

              <ChevronRight
                :size="16"
                class="shrink-0 text-slate-400 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-navy"
                aria-hidden="true"
              />
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Right: Secondary System Areas -->
      <section class="overflow-hidden rounded-2xl border border-border bg-surface lg:col-span-5">
        <div class="border-b border-border/70 px-5 py-3.5">
          <h2 class="text-sm font-bold text-navy">Phân hệ quản trị</h2>
        </div>

        <ul class="divide-y divide-border/70">
          <li v-for="area in systemAreas" :key="area.route">
            <RouterLink
              :to="{ name: area.route }"
              class="group flex items-center justify-between gap-3 px-5 py-3.5 transition-colors duration-150 hover:bg-background/70 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-teal"
            >
              <div class="flex min-w-0 items-center gap-3">
                <component
                  :is="area.icon"
                  :size="16"
                  class="shrink-0 text-slate-400 transition-colors duration-150 group-hover:text-teal"
                  aria-hidden="true"
                />
                <div class="min-w-0">
                  <p class="truncate text-sm font-semibold text-navy transition-colors duration-150 group-hover:text-teal">
                    {{ area.title }}
                  </p>
                  <p class="truncate text-xs text-slate-500">{{ area.subtitle }}</p>
                </div>
              </div>
              <ChevronRight
                :size="15"
                class="shrink-0 text-slate-300 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-navy"
                aria-hidden="true"
              />
            </RouterLink>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
