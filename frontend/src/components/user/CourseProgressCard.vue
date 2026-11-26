<script setup>
import { computed } from 'vue'
import { BookOpen, CheckCircle2, Clock3, PlayCircle } from 'lucide-vue-next'

const props = defineProps({
  entry: {
    type: Object,
    required: true,
  },
})

const course = computed(() => props.entry?.course || {})
const courseId = computed(() => course.value?.id || '')
const courseTitle = computed(() => course.value?.title || 'Khóa học chưa có tiêu đề')
const isCompleted = computed(() => props.entry?.status === 'completed' || Boolean(props.entry?.completedAt))

const hasLessons = computed(() => {
  const total = Number(props.entry?.totalLessons)
  return Number.isFinite(total) && total > 0
})

const safeCompletedLessons = computed(() => {
  const completed = Number(props.entry?.completedLessons)
  return Number.isFinite(completed) && completed >= 0 ? completed : 0
})

const safeTotalLessons = computed(() => {
  const total = Number(props.entry?.totalLessons)
  return Number.isFinite(total) && total >= 0 ? total : 0
})

const progressValue = computed(() => {
  const raw = props.entry?.progress
  if (raw === null || raw === undefined || raw === '') return null
  const num = Number(raw)
  if (!Number.isFinite(num)) return null
  return Math.min(100, Math.max(0, Math.round(num)))
})

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(date)
}

const enrolledDateLabel = computed(() => formatDate(props.entry?.enrolledAt))
const completedDateLabel = computed(() => formatDate(props.entry?.completedAt))
</script>

<template>
  <article class="bento-card flex h-full flex-col justify-between gap-4 bg-surface p-4 sm:p-5 transition-colors hover:border-teal/40">
    <div class="flex items-start gap-3.5">
      <!-- Compact Academic Cover / Thumbnail -->
      <div class="relative size-14 shrink-0 overflow-hidden rounded-lg border border-border bg-subtle">
        <img
          v-if="course.coverImageUrl"
          :src="course.coverImageUrl"
          :alt="courseTitle"
          class="h-full w-full object-cover"
          loading="lazy"
        >
        <div
          v-else
          :class="[
            'flex h-full w-full items-center justify-center',
            isCompleted ? 'bg-emerald-50 text-success' : 'bg-teal/10 text-teal',
          ]"
        >
          <CheckCircle2 v-if="isCompleted" :size="22" aria-hidden="true" />
          <BookOpen v-else :size="22" aria-hidden="true" />
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span
            :class="[
              'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold border',
              isCompleted
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-teal/25 bg-teal/10 text-teal-dark',
            ]"
          >
            <CheckCircle2 v-if="isCompleted" :size="12" aria-hidden="true" />
            <Clock3 v-else :size="12" aria-hidden="true" />
            <span>{{ isCompleted ? 'Đã hoàn thành' : 'Đang học' }}</span>
          </span>

          <span
            v-if="progressValue !== null"
            class="text-xs font-bold text-navy tabular-nums"
          >
            {{ progressValue }}%
          </span>
        </div>

        <h3 class="mt-2 line-clamp-2 text-sm sm:text-base font-bold leading-snug text-navy">
          <RouterLink
            v-if="courseId"
            :to="{ name: 'course-detail', params: { id: courseId } }"
            class="hover:text-teal transition-colors"
          >
            {{ courseTitle }}
          </RouterLink>
          <span v-else>{{ courseTitle }}</span>
        </h3>

        <p class="mt-1 text-xs text-muted">
          <template v-if="hasLessons">
            {{ safeCompletedLessons }}/{{ safeTotalLessons }} bài học
          </template>
          <template v-else>
            Khóa học chưa có bài học
          </template>
          <template v-if="completedDateLabel">
            · Hoàn thành {{ completedDateLabel }}
          </template>
          <template v-else-if="enrolledDateLabel">
            · Đăng ký {{ enrolledDateLabel }}
          </template>
        </p>
      </div>
    </div>

    <!-- Progress Bar + Action -->
    <div class="space-y-3 border-t border-border/70 pt-3.5">
      <div
        v-if="progressValue !== null"
        class="h-1.5 w-full overflow-hidden rounded-full bg-subtle"
        role="progressbar"
        :aria-valuenow="progressValue"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`Tiến độ học tập ${progressValue}%`"
      >
        <div
          :class="[
            'h-full rounded-full transition-all duration-300',
            isCompleted ? 'bg-success' : 'bg-teal',
          ]"
          :style="{ width: `${progressValue}%` }"
        />
      </div>
      <p v-else class="text-xs text-muted">
        Chưa có dữ liệu tiến độ
      </p>

      <div class="flex items-center justify-between gap-3">
        <RouterLink
          v-if="courseId"
          :to="{ name: 'course-detail', params: { id: courseId } }"
          class="text-xs font-medium text-muted hover:text-navy hover:underline"
        >
          Chi tiết khóa học
        </RouterLink>

        <RouterLink
          v-if="courseId"
          :to="{ name: 'learning', params: { courseId } }"
          :class="[
            'ui-button ui-button--sm inline-flex items-center gap-1.5 ml-auto',
            isCompleted ? 'ui-button--outline' : 'ui-button--primary',
          ]"
        >
          <PlayCircle :size="14" aria-hidden="true" />
          <span>{{ isCompleted ? 'Xem lại khóa học' : 'Tiếp tục học' }}</span>
        </RouterLink>
      </div>
    </div>
  </article>
</template>
