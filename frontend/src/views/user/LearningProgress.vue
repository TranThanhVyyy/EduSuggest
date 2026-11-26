<script setup>
import { computed, onMounted, ref } from 'vue'
import { BookOpen, CheckCircle2, Clock3, RefreshCw } from 'lucide-vue-next'
import CourseProgressCard from '@/components/user/CourseProgressCard.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { fetchMyEnrollments } from '@/service/userApiService'

const courses = ref([])
const loading = ref(true)
const error = ref('')
const activeTab = ref('all')

const isCompletedEntry = (entry) => entry?.status === 'completed' || Boolean(entry?.completedAt)

const inProgressCourses = computed(() => courses.value.filter((entry) => !isCompletedEntry(entry)))
const completedCourses = computed(() => courses.value.filter((entry) => isCompletedEntry(entry)))

const filteredCourses = computed(() => {
  if (activeTab.value === 'in_progress') return inProgressCourses.value
  if (activeTab.value === 'completed') return completedCourses.value
  return courses.value
})

const tabs = computed(() => [
  { key: 'all', label: 'Tất cả', count: courses.value.length },
  { key: 'in_progress', label: 'Đang học', count: inProgressCourses.value.length },
  { key: 'completed', label: 'Đã hoàn thành', count: completedCourses.value.length },
])

const emptyStateConfig = computed(() => {
  if (activeTab.value === 'in_progress') {
    return {
      icon: Clock3,
      title: 'Không có khóa học đang học',
      description: 'Bạn đã hoàn thành hết các khóa học hiện có hoặc chưa bắt đầu khóa học mới.',
      actionLabel: 'Khám phá thêm khóa học',
      actionRoute: { name: 'course-catalog' },
    }
  }
  if (activeTab.value === 'completed') {
    return {
      icon: CheckCircle2,
      title: 'Chưa có khóa học nào hoàn thành',
      description: 'Hoàn thành toàn bộ bài học trong một khóa học để ghi nhận hoàn thành tại đây.',
      actionLabel: courses.value.length ? 'Xem khóa học đang học' : 'Khám phá khóa học',
      actionRoute: courses.value.length ? null : { name: 'course-catalog' },
    }
  }
  return {
    icon: BookOpen,
    title: 'Bạn chưa đăng ký khóa học nào',
    description: 'Các khóa học bạn đăng ký và tiến độ học tập sẽ được tổng hợp tại đây.',
    actionLabel: 'Khám phá khóa học',
    actionRoute: { name: 'course-catalog' },
  }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    courses.value = await fetchMyEnrollments()
  } catch (cause) {
    error.value = cause.response?.data?.detail || 'Không thể tải danh sách khóa học đã đăng ký.'
  } finally {
    loading.value = false
  }
}

function handleEmptyAction() {
  if (activeTab.value === 'completed' && courses.value.length) {
    activeTab.value = 'in_progress'
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <section class="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="ui-eyebrow">Học tập của tôi</p>
        <h1 class="ui-page-title mt-1.5">Khóa học của tôi & Tiến độ</h1>
        <p class="mt-2 text-sm text-muted">
          Theo dõi tiến độ các khóa học bạn đã đăng ký và tiếp tục học bất kỳ lúc nào.
        </p>
      </div>

      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5 self-start"
        :disabled="loading"
        @click="load"
      >
        <RefreshCw :size="14" :class="{ 'animate-spin': loading }" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </section>

    <!-- Status Filter Tabs -->
    <nav
      v-if="!error"
      aria-label="Lọc trạng thái khóa học"
      class="flex flex-wrap items-center gap-2"
      role="tablist"
    >
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="activeTab === tab.key"
        :class="[
          'inline-flex items-center gap-2 rounded-lg border px-3.5 py-2 text-xs sm:text-sm font-semibold transition-colors',
          activeTab === tab.key
            ? 'border-navy bg-navy text-white'
            : 'border-border bg-surface text-ink hover:border-teal/40 hover:text-teal',
        ]"
        @click="activeTab = tab.key"
      >
        <span>{{ tab.label }}</span>
        <span
          :class="[
            'rounded-full px-2 py-0.5 text-[11px] tabular-nums',
            activeTab === tab.key ? 'bg-white/20 text-white' : 'bg-subtle text-muted',
          ]"
        >
          {{ loading ? '—' : tab.count }}
        </span>
      </button>
    </nav>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="grid gap-4 md:grid-cols-2">
      <UiSkeleton v-for="i in 4" :key="i" variant="card" />
    </div>

    <!-- Error State -->
    <UiAlert
      v-else-if="error"
      variant="danger"
      title="Không thể tải tiến độ học tập"
      :message="error"
      class="max-w-2xl"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="load"
      >
        <RefreshCw :size="14" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <!-- Courses Progress Grid -->
    <section v-else-if="filteredCourses.length" class="grid gap-4 md:grid-cols-2">
      <CourseProgressCard
        v-for="entry in filteredCourses"
        :key="entry.id"
        :entry="entry"
      />
    </section>

    <!-- Tab-Specific Empty State -->
    <UiEmptyState
      v-else
      :icon="emptyStateConfig.icon"
      :title="emptyStateConfig.title"
      :description="emptyStateConfig.description"
      :action-label="emptyStateConfig.actionLabel"
      :action-route="emptyStateConfig.actionRoute"
      @action="handleEmptyAction"
    />
  </div>
</template>
