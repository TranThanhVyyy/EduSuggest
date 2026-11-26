<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  FilePlus2,
  ImagePlus,
  Layers,
  Plus,
  Send,
} from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { authState } from '@/service/authState'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  loadProviderCategories,
  loadProviderCourses,
  providerErrorMessage,
} from '@/service/providerApiService'

const courses = ref([])
const categoryNames = ref(new Map())
const loading = ref(true)
const loadError = ref('')

const providerName = computed(() => {
  const full = authState.user?.hoTen?.trim()
  if (!full) return ''
  const parts = full.split(/\s+/)
  return parts[parts.length - 1] || full
})

const pipelineItems = [
  { key: PROVIDER_STATUS.draft, label: 'Bản nháp', dotClass: 'bg-slate-400', barClass: 'bg-slate-400', query: { status: PROVIDER_STATUS.draft } },
  { key: PROVIDER_STATUS.pending, label: 'Chờ duyệt', dotClass: 'bg-amber', barClass: 'bg-amber', query: { status: PROVIDER_STATUS.pending } },
  { key: PROVIDER_STATUS.approved, label: 'Đã xuất bản', dotClass: 'bg-teal', barClass: 'bg-teal', query: { status: PROVIDER_STATUS.approved } },
  { key: 'feedback', label: 'Cần chỉnh sửa', dotClass: 'bg-rose-500', barClass: 'bg-rose-500', query: { status: 'feedback' } },
]

const publishingSteps = [
  {
    step: '01',
    icon: ImagePlus,
    title: 'Khởi tạo khóa học & ảnh bìa',
    description: 'Thiết lập tên, danh mục, trình độ và tải lên ảnh bìa 16:9 để khóa học nổi bật trên trang khám phá.',
  },
  {
    step: '02',
    icon: Layers,
    title: 'Xây dựng đề cương bài giảng',
    description: 'Tổ chức danh sách bài học mạch lạc, bổ sung mô tả mục tiêu và đính kèm học liệu hỗ trợ.',
  },
  {
    step: '03',
    icon: Send,
    title: 'Gửi Chuyên gia thẩm định',
    description: 'Theo dõi trạng thái phê duyệt, nhận góp ý chuyên môn và xuất bản công khai tới người học.',
  },
]

const qualityChecklist = [
  'Ảnh bìa tỷ lệ 16:9 rõ nét (JPG, PNG hoặc WEBP, tối đa 5MB).',
  'Tiêu đề khóa học nêu rõ chủ đề và đối tượng mục tiêu.',
  'Cấu trúc tối thiểu 3 bài học sắp xếp theo trình tự tiếp thu.',
  'Tài liệu tham khảo đúng định dạng PDF, slide hoặc mã nguồn.',
]

const counts = computed(() => {
  const list = courses.value
  return {
    total: list.length,
    [PROVIDER_STATUS.draft]: list.filter((c) => c.status === PROVIDER_STATUS.draft).length,
    [PROVIDER_STATUS.pending]: list.filter((c) => c.status === PROVIDER_STATUS.pending).length,
    [PROVIDER_STATUS.approved]: list.filter((c) => c.status === PROVIDER_STATUS.approved).length,
    feedback: list.filter((c) =>
      [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(c.status),
    ).length,
  }
})

const recentCourses = computed(() => {
  return [...courses.value]
    .sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0))
    .slice(0, 6)
    .map((course) => ({
      ...course,
      categoryName: categoryNames.value.get(String(course.categoryId)) || 'Chưa phân loại',
      editable: [
        PROVIDER_STATUS.draft,
        PROVIDER_STATUS.rejected,
        PROVIDER_STATUS.changesRequested,
      ].includes(course.status),
    }))
})

const coursesMissingCover = computed(() =>
  courses.value.filter(
    (c) =>
      !c.coverImageUrl &&
      [PROVIDER_STATUS.draft, PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(c.status),
  ),
)

async function loadData() {
  loading.value = true
  loadError.value = ''
  const [coursesRes, categoriesRes] = await Promise.allSettled([
    loadProviderCourses(),
    loadProviderCategories(),
  ])
  if (coursesRes.status === 'fulfilled') {
    courses.value = coursesRes.value
  } else {
    loadError.value = providerErrorMessage(coursesRes.reason, 'Không thể tải danh sách khóa học.')
  }
  if (categoriesRes.status === 'fulfilled') {
    categoryNames.value = new Map(categoriesRes.value.map((c) => [String(c.id), c.name]))
  }
  loading.value = false
}

onMounted(loadData)

function statusShare(key) {
  if (!counts.value.total) return 0
  return Math.round((counts.value[key] / counts.value.total) * 100)
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}
</script>

<template>
  <div class="space-y-8">
    <!-- Editorial Page Header + Single Create Action Pair -->
    <section class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1">
        <h1 class="font-display text-2xl font-bold tracking-tight text-navy sm:text-[28px]">
          {{ providerName ? `Xin chào, ${providerName}` : 'Tổng quan' }}
        </h1>
        <p v-if="!loading && !loadError" class="text-sm text-slate-600">
          <template v-if="counts.total > 0">
            Đang quản lý <strong class="font-semibold text-navy">{{ counts.total }} khóa học</strong>
            <span v-if="counts[PROVIDER_STATUS.approved]"> · {{ counts[PROVIDER_STATUS.approved] }} đã xuất bản</span>
            <span v-if="counts[PROVIDER_STATUS.pending]"> · {{ counts[PROVIDER_STATUS.pending] }} chờ duyệt</span>.
          </template>
          <template v-else>
            Sẵn sàng biên soạn và xuất bản khóa học đầu tiên của bạn trên EduSuggest.
          </template>
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 shrink-0">
        <RouterLink
          :to="{ name: 'provider-materials-manage', query: { create: '1' } }"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
        >
          <FilePlus2 :size="15" class="text-teal" aria-hidden="true" />
          <span>Tạo tài liệu</span>
        </RouterLink>
        <RouterLink
          :to="{ name: 'provider-course-create' }"
          class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
        >
          <Plus :size="15" aria-hidden="true" />
          <span>Tạo khóa học</span>
        </RouterLink>
      </div>
    </section>

    <UiAlert
      v-if="loadError"
      variant="danger"
      title="Không thể tải dữ liệu khóa học"
      :message="loadError"
    />

    <!-- Structured Publishing Pipeline Ledger -->
    <section
      aria-label="Trạng thái xuất bản khóa học"
      class="overflow-hidden rounded-2xl border border-border bg-surface"
    >
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 px-5 py-3">
        <div class="flex items-center gap-2.5">
          <span class="text-xs font-semibold text-navy">Tiến độ xuất bản</span>
          <span class="text-xs text-slate-400" aria-hidden="true">·</span>
          <span class="text-xs text-slate-500 tabular-nums">
            {{ loading ? 'Đang tải…' : `${counts.total} khóa học` }}
          </span>
        </div>

        <div
          class="flex h-1.5 w-36 overflow-hidden rounded-full bg-subtle"
          role="presentation"
          aria-hidden="true"
        >
          <span
            v-for="item in pipelineItems"
            :key="`bar-${item.key}`"
            class="h-full transition-[width] duration-300"
            :class="item.barClass"
            :style="{ width: `${statusShare(item.key)}%` }"
          ></span>
        </div>
      </div>

      <div class="grid grid-cols-2 divide-y divide-border/70 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        <RouterLink
          v-for="item in pipelineItems"
          :key="item.key"
          :to="{ name: 'provider-courses', query: item.query }"
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
              {{ loading ? '…' : counts[item.key] }}
            </span>
            <span class="text-[11px] font-medium text-slate-400 tabular-nums">
              {{ counts.total ? `${statusShare(item.key)}%` : '—' }}
            </span>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- Loading Skeleton -->
    <section v-if="loading" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <UiSkeleton v-for="i in 3" :key="i" variant="rect" height="240px" rounded="1rem" />
    </section>

    <!-- State A: Visual Course Studio Grid (when provider has courses) -->
    <template v-else-if="recentCourses.length">
      <!-- Subtle Inline Cover Reminder -->
      <div
        v-if="coursesMissingCover.length"
        class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal/25 bg-teal/[0.04] px-4 py-3 text-sm"
      >
        <div class="flex items-center gap-2.5 text-slate-700">
          <ImagePlus :size="16" class="shrink-0 text-teal" aria-hidden="true" />
          <span>
            Có <strong class="font-semibold text-navy">{{ coursesMissingCover.length }} khóa học</strong> chưa cập nhật ảnh bìa. Thêm ảnh 16:9 giúp khóa học nổi bật hơn khi hiển thị công khai.
          </span>
        </div>
        <RouterLink
          :to="{ name: 'provider-course-edit', params: { id: coursesMissingCover[0].id } }"
          class="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-teal hover:underline"
        >
          <span>Thêm ảnh bìa</span>
          <ArrowRight :size="13" aria-hidden="true" />
        </RouterLink>
      </div>

      <section class="space-y-4">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-base font-bold text-navy">Khóa học gần đây</h2>
          <RouterLink
            :to="{ name: 'provider-courses' }"
            class="inline-flex items-center gap-1 text-xs font-semibold text-teal hover:underline sm:text-sm"
          >
            <span>Xem tất cả</span>
            <ArrowRight :size="14" aria-hidden="true" />
          </RouterLink>
        </div>

        <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="course in recentCourses"
            :key="course.id"
            class="es-card-interactive group flex flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-xs"
          >
            <!-- 16:9 Cover Media -->
            <RouterLink
              :to="{ name: 'provider-course-detail', params: { id: course.id } }"
              class="relative block aspect-[16/9] w-full overflow-hidden border-b border-border/70 bg-subtle"
            >
              <img
                v-if="course.coverImageUrl"
                :src="course.coverImageUrl"
                :alt="`Ảnh bìa ${course.title}`"
                class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
              >
              <div
                v-else
                class="flex h-full w-full flex-col items-center justify-center gap-1.5 bg-gradient-to-br from-subtle to-slate-100 text-slate-400"
              >
                <ImagePlus :size="22" aria-hidden="true" />
                <span class="text-[11px] font-medium">Chưa có ảnh bìa</span>
              </div>

              <div class="absolute left-3 top-3">
                <UiStatusBadge
                  :status="course.status"
                  :label="PROVIDER_STATUS_LABELS[course.status] || course.status"
                />
              </div>
            </RouterLink>

            <!-- Card Content -->
            <div class="flex flex-1 flex-col p-4">
              <p class="truncate text-xs font-medium text-teal-dark">
                {{ course.categoryName }}
              </p>

              <RouterLink
                :to="{ name: 'provider-course-detail', params: { id: course.id } }"
                class="mt-1 line-clamp-2 text-[15px] font-bold leading-snug text-navy transition-colors duration-150 hover:text-teal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
              >
                {{ course.title || 'Khóa học chưa đặt tên' }}
              </RouterLink>

              <p class="mt-2 text-xs text-slate-500">
                {{ course.lessons.length }} bài học · Cập nhật {{ formatDate(course.updatedAt) }}
              </p>

              <div class="mt-auto flex items-center justify-between gap-2 border-t border-border/60 pt-3.5">
                <RouterLink
                  :to="{ name: 'provider-course-detail', params: { id: course.id } }"
                  class="text-xs font-semibold text-slate-600 transition-colors duration-150 hover:text-navy"
                >
                  Chi tiết khóa học
                </RouterLink>
                <RouterLink
                  v-if="course.editable"
                  :to="{ name: 'provider-course-edit', params: { id: course.id } }"
                  class="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 text-xs font-semibold text-navy transition-colors duration-150 hover:border-teal/50 hover:text-teal"
                >
                  <span>Chỉnh sửa</span>
                </RouterLink>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>

    <!-- State B: Refined 2-Column Creator Onboarding Studio (when 0 courses) -->
    <section v-else class="grid gap-6 lg:grid-cols-12 items-start">
      <!-- Left: 3-Step Publishing Journey -->
      <article class="rounded-2xl border border-border bg-surface p-6 shadow-xs sm:p-8 lg:col-span-7">
        <div class="space-y-1.5">
          <p class="text-xs font-semibold uppercase tracking-[0.1em] text-teal-dark">
            Bắt đầu xuất bản
          </p>
          <h2 class="font-display text-xl font-bold text-navy">
            Quy trình đưa khóa học lên EduSuggest
          </h2>
          <p class="text-sm text-slate-600">
            Hoàn thiện 3 bước dưới đây để khóa học của bạn sẵn sàng thẩm định và tiếp cận người học.
          </p>
        </div>

        <ol class="mt-6 space-y-5">
          <li
            v-for="item in publishingSteps"
            :key="item.step"
            class="flex items-start gap-4"
          >
            <span class="flex size-10 shrink-0 items-center justify-center rounded-xl border border-border bg-subtle/80 text-navy">
              <component :is="item.icon" :size="18" class="text-teal-dark" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <p class="text-sm font-bold text-navy">
                <span class="mr-1.5 font-mono text-xs font-semibold text-slate-400">{{ item.step }}</span>
                {{ item.title }}
              </p>
              <p class="mt-0.5 text-xs leading-relaxed text-slate-600">
                {{ item.description }}
              </p>
            </div>
          </li>
        </ol>
      </article>

      <!-- Right: Editorial Quality Checklist -->
      <aside class="rounded-2xl border border-border bg-subtle/60 p-6 sm:p-7 lg:col-span-5 space-y-5">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Tiêu chuẩn kiểm duyệt
          </p>
          <h3 class="text-base font-bold text-navy">
            Gợi ý để được duyệt nhanh hơn
          </h3>
        </div>

        <ul class="space-y-3">
          <li
            v-for="tip in qualityChecklist"
            :key="tip"
            class="flex items-start gap-2.5 text-xs leading-relaxed text-slate-700"
          >
            <CheckCircle2 :size="15" class="mt-0.5 shrink-0 text-teal" aria-hidden="true" />
            <span>{{ tip }}</span>
          </li>
        </ul>

        <div class="border-t border-border/80 pt-4">
          <RouterLink
            :to="{ name: 'provider-reviews' }"
            class="inline-flex items-center gap-1.5 text-xs font-semibold text-navy transition-colors duration-150 hover:text-teal"
          >
            <span>Xem khu vực theo dõi kiểm duyệt</span>
            <ArrowRight :size="13" aria-hidden="true" />
          </RouterLink>
        </div>
      </aside>
    </section>
  </div>
</template>
