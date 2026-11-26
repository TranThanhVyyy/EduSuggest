<script setup>
import { computed, ref } from 'vue'
import { BookOpen, CheckCircle2, Clock3, Code2, Cpu, Database, Globe, GraduationCap, Heart, Layers, Star } from 'lucide-vue-next'
import ReasonBadgeList from '@/components/user/ReasonBadgeList.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import { authState } from '@/service/authState'
import { getRoleName } from '@/service/authService'
import { commerceErrorMessage } from '@/service/commerceApiService'
import {
  commerceState,
  isCourseEnrolled,
  isCourseWishlisted,
  showCommerceToast,
  toggleWishlistCourse,
} from '@/service/commerceState'
import { formatCourseLevel, formatDurationMinutes } from '@/utils/courseDisplay'

const props = defineProps({
  course: {
    type: Object,
    required: true,
  },
  reasonCodes: {
    type: Array,
    default: null,
  },
  showReasons: {
    type: Boolean,
    default: true,
  },
})

const ACADEMIC_THEMES = [
  { bg: 'bg-navy/[0.04]', accent: 'bg-teal', iconBg: 'bg-teal/10 text-teal', icon: BookOpen },
  { bg: 'bg-teal/[0.05]', accent: 'bg-navy', iconBg: 'bg-navy/10 text-navy', icon: Code2 },
  { bg: 'bg-amber/[0.06]', accent: 'bg-amber', iconBg: 'bg-amber/15 text-amber-dark', icon: Layers },
  { bg: 'bg-slate-100', accent: 'bg-teal-dark', iconBg: 'bg-white text-navy border border-border', icon: Cpu },
  { bg: 'bg-navy/[0.04]', accent: 'bg-amber', iconBg: 'bg-white text-teal border border-border', icon: Database },
  { bg: 'bg-subtle', accent: 'bg-navy', iconBg: 'bg-teal/10 text-teal-dark', icon: Globe },
]

const coverTheme = computed(() => {
  const seed = Number(props.course?.categoryId) || Number(props.course?.id) || 0
  return ACADEMIC_THEMES[Math.abs(seed) % ACADEMIC_THEMES.length]
})

const cleanCategory = computed(() => {
  const value = String(props.course?.category || '').trim()
  if (!value || value === 'Chưa phân loại' || /^Danh mục #\d+$/.test(value)) return ''
  return value
})

const cleanProvider = computed(() => {
  const value = String(props.course?.provider || '').trim()
  if (!value || value === 'Chưa có thông tin' || /^Nhà cung cấp #\d+$/.test(value)) return ''
  return value
})

const cleanLevel = computed(() => formatCourseLevel(props.course?.level))
const cleanDuration = computed(() => formatDurationMinutes(props.course?.duration))

const effectiveReasonCodes = computed(() => {
  if (!props.showReasons) return []
  if (Array.isArray(props.reasonCodes)) return props.reasonCodes
  return Array.isArray(props.course?.reasonCodes) ? props.course.reasonCodes : []
})

const canUseWishlist = computed(
  () => Boolean(authState.accessToken && authState.user && getRoleName() === 'USER' && commerceState.marketplaceEnabled && props.course?.id),
)
const wishlisted = computed(() => (props.course?.id ? isCourseWishlisted(props.course.id) : false))
const owned = computed(() => (props.course?.id ? isCourseEnrolled(props.course.id) : false))
const wishlistBusy = ref(false)

async function handleWishlistToggle() {
  if (!canUseWishlist.value || wishlistBusy.value) return
  wishlistBusy.value = true
  try {
    await toggleWishlistCourse(props.course.id)
  } catch (error) {
    showCommerceToast(commerceErrorMessage(error, 'Không thể cập nhật danh sách yêu thích.'), 'error')
  } finally {
    wishlistBusy.value = false
  }
}

function formatPrice(price) {
  if (price === null || price === undefined || price === '') {
    return 'Chưa có thông tin'
  }
  const numericPrice = Number(price)
  if (Number.isNaN(numericPrice)) {
    return 'Chưa có thông tin'
  }
  return numericPrice > 0
    ? `${new Intl.NumberFormat('vi-VN').format(numericPrice)} ₫`
    : 'Miễn phí'
}
</script>

<template>
  <article class="es-card-interactive group relative flex h-full flex-col overflow-hidden rounded-xl border border-border bg-surface hover:border-teal/40 hover:shadow-md focus-within:border-teal/60 focus-within:ring-2 focus-within:ring-teal/20">
    <!-- Cover Image (16:9 clean frame, zero text-clashing overlays) or Minimal Academic Cover -->
    <div class="relative aspect-video w-full overflow-hidden border-b border-border/70 bg-subtle">
      <img
        v-if="course.coverImageUrl"
        :src="course.coverImageUrl"
        :alt="course.title"
        class="es-cover-zoom h-full w-full object-cover"
        loading="lazy"
      >
      <div
        v-else
        :class="['relative flex h-full w-full flex-col justify-between p-4', coverTheme.bg]"
      >
        <div :class="['absolute inset-y-0 left-0 w-1', coverTheme.accent]" aria-hidden="true" />
        <div class="flex items-start justify-between gap-2 pl-1">
          <span
            v-if="cleanCategory"
            class="inline-flex max-w-[75%] truncate rounded-md bg-navy px-2 py-0.5 text-[11px] font-semibold text-white"
          >
            {{ cleanCategory }}
          </span>
          <span v-else class="text-[11px] font-semibold uppercase tracking-wider text-muted">
            Khóa học
          </span>

          <span
            v-if="cleanLevel"
            class="shrink-0 rounded-md border border-border bg-surface px-2 py-0.5 text-[11px] font-medium text-ink"
          >
            {{ cleanLevel }}
          </span>
        </div>

        <div class="flex items-end justify-between pl-1">
          <div :class="['flex size-10 items-center justify-center rounded-lg', coverTheme.iconBg]">
            <component :is="coverTheme.icon" :size="20" aria-hidden="true" />
          </div>
          <span class="text-[11px] font-semibold tracking-wide text-slate-600">
            EduSuggest
          </span>
        </div>
      </div>

      <div v-if="course.status" class="absolute right-2.5 top-2.5">
        <UiStatusBadge :status="course.status" />
      </div>
      <button
        v-else-if="canUseWishlist"
        type="button"
        class="absolute right-2.5 top-2.5 flex size-8 items-center justify-center rounded-full border border-border/70 bg-surface/92 text-navy shadow-sm transition-[background-color,color,transform] duration-150 hover:bg-surface active:scale-[0.94] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/50"
        :aria-pressed="wishlisted"
        :aria-label="wishlisted ? 'Bỏ khỏi danh sách yêu thích' : 'Thêm vào danh sách yêu thích'"
        :title="wishlisted ? 'Bỏ yêu thích' : 'Lưu vào yêu thích'"
        :disabled="wishlistBusy"
        @click.stop.prevent="handleWishlistToggle"
      >
        <Heart
          :size="15"
          :class="wishlisted ? 'fill-rose-500 text-rose-500' : 'text-navy/80'"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Content Body -->
    <div class="flex flex-1 flex-col gap-2.5 p-4">
      <!-- Category & Level Metadata Pills (moved cleanly out of cover photo) -->
      <div
        v-if="course.coverImageUrl && (cleanCategory || cleanLevel)"
        class="flex flex-wrap items-center gap-1.5"
      >
        <span
          v-if="cleanCategory"
          class="inline-flex max-w-[68%] truncate rounded-md bg-navy/[0.07] px-2 py-0.5 text-[11px] font-semibold text-navy"
        >
          {{ cleanCategory }}
        </span>
        <span
          v-if="cleanLevel"
          class="inline-flex shrink-0 items-center rounded-md border border-border/80 bg-subtle px-2 py-0.5 text-[11px] font-medium text-slate-700"
        >
          {{ cleanLevel }}
        </span>
      </div>

      <h3 class="line-clamp-2 text-[15px] font-bold leading-snug text-navy transition-colors group-hover:text-teal">
        <RouterLink
          :to="{ name: 'course-detail', params: { id: course.id } }"
          class="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        >
          {{ course.title }}
        </RouterLink>
      </h3>

      <!-- Compact Metadata -->
      <div
        v-if="cleanProvider || cleanDuration || (course.rating !== null && course.rating !== undefined)"
        class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted"
      >
        <span v-if="cleanProvider" class="inline-flex items-center gap-1 font-medium text-ink">
          <GraduationCap :size="13" class="shrink-0 text-teal" aria-hidden="true" />
          <span class="max-w-[150px] truncate">{{ cleanProvider }}</span>
        </span>

        <span v-if="cleanDuration" class="inline-flex items-center gap-1">
          <Clock3 :size="13" class="shrink-0 text-muted" aria-hidden="true" />
          <span>{{ cleanDuration }}</span>
        </span>

        <span
          v-if="course.rating !== null && course.rating !== undefined"
          class="inline-flex items-center gap-1 font-semibold text-ink"
        >
          <Star :size="13" class="shrink-0 fill-amber text-amber" aria-hidden="true" />
          <span>{{ course.rating }}</span>
          <span v-if="course.reviewCount" class="font-normal text-muted">({{ course.reviewCount }})</span>
        </span>
      </div>

      <!-- Recommendation Reason Badges -->
      <div v-if="effectiveReasonCodes.length">
        <ReasonBadgeList :reason-codes="effectiveReasonCodes" :max-visible="2" />
      </div>

      <!-- Footer: Price & Action -->
      <div class="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border/80 pt-3.5">
        <div class="min-w-0">
          <span
            v-if="owned"
            class="inline-flex items-center gap-1 rounded-full bg-teal/10 px-2.5 py-0.5 text-[11px] font-semibold text-teal-dark"
          >
            <CheckCircle2 :size="12" aria-hidden="true" />
            <span>Đã sở hữu</span>
          </span>
          <template v-else>
            <span class="block text-[11px] font-semibold uppercase tracking-wider text-slate-600">Học phí</span>
            <span class="text-sm font-bold text-navy tabular-nums">
              {{ formatPrice(course.price) }}
            </span>
          </template>
        </div>

        <RouterLink
          v-if="owned"
          :to="{ name: 'learning', params: { courseId: course.id } }"
          class="ui-button ui-button--outline ui-button--sm shrink-0 whitespace-nowrap active:scale-[0.97]"
        >
          Vào học
        </RouterLink>
        <RouterLink
          v-else
          :to="{ name: 'course-detail', params: { id: course.id } }"
          class="ui-button ui-button--primary ui-button--sm shrink-0 whitespace-nowrap active:scale-[0.97]"
        >
          Xem chi tiết
        </RouterLink>
      </div>
    </div>
  </article>
</template>
