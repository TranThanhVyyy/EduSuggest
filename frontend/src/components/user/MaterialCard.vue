<script setup>
import { computed } from 'vue'
import { BookOpen, Download, FileText, Layers } from 'lucide-vue-next'
import ReasonBadgeList from '@/components/user/ReasonBadgeList.vue'

const props = defineProps({
  material: {
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

const cleanCategory = computed(() => {
  const value = String(props.material?.categoryName || props.material?.category || '').trim()
  if (!value || /^Danh mục #\d+$/.test(value)) return ''
  return value
})

const cleanProvider = computed(() => {
  const value = String(props.material?.provider || '').trim()
  if (!value || /^Nhà cung cấp #\d+$/.test(value)) return ''
  return value
})

const effectiveReasonCodes = computed(() => {
  if (!props.showReasons) return []
  if (Array.isArray(props.reasonCodes)) return props.reasonCodes
  return Array.isArray(props.material?.reasonCodes) ? props.material.reasonCodes : []
})
</script>

<template>
  <article class="es-card-interactive group relative flex h-full flex-col overflow-hidden rounded-xl border border-border bg-surface p-4 sm:p-5 hover:border-teal/40 hover:shadow-md focus-within:border-teal/60 focus-within:ring-2 focus-within:ring-teal/20">
    <!-- Header with Icon & Format Tag -->
    <div class="flex items-start gap-3">
      <div class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-teal/20 bg-teal/10 text-teal transition-colors group-hover:bg-teal group-hover:text-white">
        <FileText :size="19" aria-hidden="true" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
          <span v-if="material.type" class="rounded-md border border-border bg-subtle px-2 py-0.5 font-semibold text-ink">
            {{ material.type }}
          </span>
          <span v-if="cleanCategory" class="max-w-[140px] truncate rounded-md bg-navy px-2 py-0.5 font-medium text-white">
            {{ cleanCategory }}
          </span>
        </div>

        <h3 class="mt-1.5 line-clamp-2 text-sm font-bold leading-snug text-navy transition-colors group-hover:text-teal">
          <RouterLink
            :to="{ name: 'material-detail', params: { id: material.id } }"
            class="rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
          >
            {{ material.title }}
          </RouterLink>
        </h3>
      </div>
    </div>

    <!-- Description -->
    <p v-if="material.description" class="mt-2.5 line-clamp-2 text-xs leading-relaxed text-muted">
      {{ material.description }}
    </p>

    <!-- Recommendation Reason Badges -->
    <div v-if="effectiveReasonCodes.length" class="mt-3">
      <ReasonBadgeList :reason-codes="effectiveReasonCodes" :max-visible="2" />
    </div>

    <!-- Context info (only when real API titles exist) -->
    <div
      v-if="material.courseTitle || material.courseId || material.lessonTitle || material.lessonId || material.sizeLabel"
      class="mt-3 space-y-1 border-t border-border/60 pt-2.5 text-xs text-muted"
    >
      <p v-if="material.courseTitle" class="flex items-center gap-1.5 truncate">
        <BookOpen :size="13" class="shrink-0 text-muted" aria-hidden="true" />
        <span class="truncate">Khóa học: {{ material.courseTitle }}</span>
      </p>
      <p v-else-if="material.courseId" class="flex items-center gap-1.5 truncate">
        <BookOpen :size="13" class="shrink-0 text-muted" aria-hidden="true" />
        <span class="truncate">Mã khóa học: {{ material.courseId }}</span>
      </p>

      <p v-if="material.lessonTitle" class="flex items-center gap-1.5 truncate">
        <Layers :size="13" class="shrink-0 text-muted" aria-hidden="true" />
        <span class="truncate">Bài học: {{ material.lessonTitle }}</span>
      </p>
      <p v-else-if="material.lessonId" class="flex items-center gap-1.5 truncate">
        <Layers :size="13" class="shrink-0 text-muted" aria-hidden="true" />
        <span class="truncate">Mã bài học: {{ material.lessonId }}</span>
      </p>

      <p v-if="material.sizeLabel" class="text-[11px] text-muted">
        Dung lượng: {{ material.sizeLabel }}
      </p>
    </div>

    <!-- Footer & Link -->
    <div class="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border/80 pt-3.5">
      <span v-if="cleanProvider" class="min-w-0 flex-1 truncate text-xs font-medium text-ink">
        {{ cleanProvider }}
      </span>
      <span v-else class="text-xs text-muted">
        Tài liệu học tập
      </span>

      <RouterLink
        :to="{ name: 'material-detail', params: { id: material.id } }"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5 shrink-0 whitespace-nowrap"
      >
        <Download :size="13" aria-hidden="true" />
        <span>Xem tài liệu</span>
      </RouterLink>
    </div>
  </article>
</template>
