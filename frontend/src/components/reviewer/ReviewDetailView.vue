<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  ExternalLink,
  FileText,
  XCircle,
} from 'lucide-vue-next'
import { REVIEWABLE_STATUSES } from '@/constant/reviewStatus'
import ReviewActionModal from '@/components/reviewer/ReviewActionModal.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  getExpertCourse,
  submitExpertCourseDecision,
  getExpertMaterial,
  submitExpertMaterialDecision,
} from '@/service/expertApiService'

const route = useRoute()
const props = defineProps({ kind: { type: String, required: true } })
const item = ref(null)
const loading = ref(false)
const loadError = ref('')
const isForbidden = ref(false)
const actionError = ref('')
const actionModalOpen = ref(false)
const selectedAction = ref('')
const saving = ref(false)
const isCourse = computed(() => props.kind === 'course')
const canReview = computed(() => item.value && REVIEWABLE_STATUSES.includes(item.value.status))
const queueRoute = computed(() => ({ name: isCourse.value ? 'reviewer-courses' : 'reviewer-materials' }))

async function loadDetail(id) {
  item.value = null
  loadError.value = ''
  isForbidden.value = false
  loading.value = true
  try {
    item.value = isCourse.value
      ? await getExpertCourse(id)
      : await getExpertMaterial(id)
  } catch (error) {
    isForbidden.value = error.response?.status === 403
    loadError.value = error.response?.data?.detail || `Không thể tải ${isCourse.value ? 'khóa học' : 'tài liệu'}. Hãy quay lại danh sách hoặc thử lại.`
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, loadDetail, { immediate: true })

function startAction(action) {
  actionError.value = ''
  selectedAction.value = action
  actionModalOpen.value = true
}

async function confirmAction({ action, note }) {
  if (!item.value || saving.value) return
  saving.value = true
  actionError.value = ''
  try {
    const updated = isCourse.value
      ? await submitExpertCourseDecision(item.value.id, action, note)
      : await submitExpertMaterialDecision(item.value.id, action, note)
    item.value = {
      ...item.value,
      ...updated,
      lectures: item.value.lectures || [],
      attachments: item.value.attachments || [],
    }
    actionModalOpen.value = false
  } catch (error) {
    actionError.value = error.response?.data?.detail || 'Không thể lưu quyết định kiểm duyệt. Hãy thử lại.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <RouterLink
      :to="queueRoute"
      class="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 transition-colors duration-150 hover:text-navy"
    >
      <ArrowLeft :size="15" aria-hidden="true" />
      <span>Quay lại danh sách chờ duyệt</span>
    </RouterLink>

    <div v-if="loading" class="space-y-4">
      <UiSkeleton variant="rect" height="120px" rounded="1rem" />
      <UiSkeleton variant="rect" height="260px" rounded="1rem" />
    </div>

    <section
      v-else-if="loadError"
      class="max-w-2xl rounded-2xl border p-6 space-y-3"
      :class="isForbidden ? 'border-amber/30 bg-amber/[0.05]' : 'border-border bg-surface'"
      role="alert"
    >
      <h1 class="font-display text-xl font-bold text-navy">
        {{ isForbidden ? 'Chưa đủ điều kiện kiểm duyệt' : 'Không thể mở nội dung' }}
      </h1>
      <p class="text-sm leading-6 text-slate-600">{{ loadError }}</p>
      <div v-if="isForbidden" class="pt-1">
        <RouterLink
          :to="{ name: 'reviewer-profile' }"
          class="inline-flex h-9 items-center justify-center rounded-lg bg-teal px-4 text-xs font-semibold text-white hover:bg-teal-dark"
        >
          Hoàn thiện hồ sơ chuyên môn
        </RouterLink>
      </div>
    </section>

    <!-- 2-Column Editorial Review Workbench -->
    <div v-else-if="item" class="grid gap-6 lg:grid-cols-[1fr_320px] items-start">
      <!-- Left: Content Inspection -->
      <div class="space-y-6">
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-5">
          <header class="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 pb-5">
            <div class="min-w-0 flex-1 space-y-1.5">
              <p class="text-xs font-semibold uppercase tracking-[0.08em] text-teal-dark">
                {{ isCourse ? 'Khóa học' : 'Tài liệu' }} #{{ item.id }}
              </p>
              <h1 class="font-display text-2xl font-bold tracking-tight text-navy">
                {{ item.title }}
              </h1>
              <p class="whitespace-pre-line text-sm leading-relaxed text-slate-600">
                {{ item.description || 'Chưa có mô tả chi tiết.' }}
              </p>
            </div>
            <UiStatusBadge :status="item.status" class="shrink-0" />
          </header>

          <dl class="grid gap-4 sm:grid-cols-3 text-xs">
            <div class="rounded-xl bg-background/80 px-3.5 py-3">
              <dt class="font-medium text-slate-500">Danh mục</dt>
              <dd class="mt-1 font-semibold text-navy">{{ item.category || 'Chưa phân loại' }}</dd>
            </div>
            <div class="rounded-xl bg-background/80 px-3.5 py-3">
              <dt class="font-medium text-slate-500">Nhà cung cấp</dt>
              <dd class="mt-1 font-semibold text-navy">{{ item.provider || 'Chưa có dữ liệu' }}</dd>
            </div>
            <div v-if="isCourse" class="rounded-xl bg-background/80 px-3.5 py-3">
              <dt class="font-medium text-slate-500">Học phí</dt>
              <dd class="mt-1 font-semibold text-navy">
                {{ item.price == null ? 'Chưa xác định' : (item.price === 0 ? 'Miễn phí' : new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(item.price)) }}
              </dd>
            </div>
            <div v-else class="rounded-xl bg-background/80 px-3.5 py-3">
              <dt class="font-medium text-slate-500">Định dạng</dt>
              <dd class="mt-1 font-semibold uppercase text-navy">{{ item.type || 'DOCUMENT' }}</dd>
            </div>
          </dl>
        </section>

        <!-- Course Lessons Inspection -->
        <section v-if="isCourse" class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <h2 class="text-base font-bold text-navy">
            Đề cương bài học ({{ item.lectures.length }})
          </h2>

          <ol v-if="item.lectures.length" class="divide-y divide-border/70 border-y border-border/70">
            <li v-for="(lesson, index) in item.lectures" :key="lesson.id" class="py-4 space-y-2">
              <div class="flex items-center justify-between gap-2">
                <h3 class="text-sm font-semibold text-navy">
                  <span class="mr-2 font-mono text-xs text-slate-400">{{ String(index + 1).padStart(2, '0') }}</span>
                  {{ lesson.title }}
                </h3>
                <span v-if="lesson.duration" class="shrink-0 text-xs text-slate-500 tabular-nums">
                  {{ lesson.duration }} phút
                </span>
              </div>
              <p v-if="lesson.content" class="whitespace-pre-line text-sm leading-relaxed text-slate-600">
                {{ lesson.content }}
              </p>
              <ul v-if="lesson.attachments.length" class="space-y-1.5 pt-1">
                <li
                  v-for="file in lesson.attachments"
                  :key="file.name"
                  class="flex items-center justify-between gap-2 rounded-lg border border-border/70 bg-background/70 px-3 py-2 text-xs"
                >
                  <span class="flex min-w-0 items-center gap-2 font-medium text-navy">
                    <FileText :size="14" class="shrink-0 text-teal" aria-hidden="true" />
                    <span class="truncate">{{ file.name }}</span>
                  </span>
                  <a
                    v-if="file.url"
                    :href="file.url"
                    target="_blank"
                    rel="noreferrer"
                    class="inline-flex shrink-0 items-center gap-1 font-semibold text-teal hover:underline"
                  >
                    <span>Mở tệp</span>
                    <ExternalLink :size="12" aria-hidden="true" />
                  </a>
                </li>
              </ul>
            </li>
          </ol>

          <p v-else class="rounded-xl border border-dashed border-border p-6 text-center text-sm text-slate-500">
            Khóa học chưa có bài học nào.
          </p>
        </section>

        <!-- Standalone Material File Inspection -->
        <section v-else class="rounded-2xl border border-border bg-surface p-6 space-y-3">
          <h2 class="text-base font-bold text-navy">Tệp tài liệu đính kèm</h2>
          <p class="text-xs text-slate-500">Kiểm tra liên kết tệp gốc do nhà cung cấp gửi lên trước khi đưa ra quyết định:</p>
          <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-background/80 px-4 py-3.5">
            <div class="flex min-w-0 items-center gap-2.5">
              <FileText :size="18" class="shrink-0 text-teal" aria-hidden="true" />
              <a
                v-if="item.fileUrl"
                :href="item.fileUrl"
                target="_blank"
                rel="noreferrer"
                class="break-all text-sm font-medium text-navy underline decoration-teal/50 underline-offset-2 hover:text-teal"
              >
                {{ item.fileUrl }}
              </a>
              <span v-else class="text-sm text-slate-500">Chưa có liên kết tệp</span>
            </div>
            <a
              v-if="item.fileUrl"
              :href="item.fileUrl"
              target="_blank"
              rel="noreferrer"
              class="ui-button ui-button--outline ui-button--sm inline-flex shrink-0 items-center gap-1.5"
            >
              <span>Mở liên kết</span>
              <ExternalLink :size="13" aria-hidden="true" />
            </a>
          </div>
        </section>
      </div>

      <!-- Right: Sticky Decision Panel -->
      <aside class="rounded-2xl border border-border bg-surface p-5 space-y-4 lg:sticky lg:top-20">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Kết luận thẩm định</p>
          <h2 class="text-base font-bold text-navy">Quyết định kiểm duyệt</h2>
        </div>

        <p v-if="item.reviewNote" class="rounded-xl border border-border bg-background/80 p-3 text-xs leading-relaxed text-slate-700">
          <strong class="block font-semibold text-navy mb-1">Ghi chú gần nhất:</strong>
          {{ item.reviewNote }}
        </p>

        <p v-if="actionError" class="rounded-xl border border-danger/25 bg-danger/5 px-3 py-2.5 text-xs text-danger" role="alert">
          {{ actionError }}
        </p>

        <div v-if="canReview" class="space-y-2.5">
          <button
            type="button"
            :disabled="saving"
            class="flex w-full items-center justify-center gap-2 rounded-xl bg-teal px-4 py-2.5 text-sm font-semibold text-white shadow-[0_1px_2px_rgba(13,148,136,0.22)] transition-colors duration-150 hover:bg-teal-dark disabled:opacity-60"
            @click="startAction('approve')"
          >
            <Check :size="16" aria-hidden="true" />
            <span>Phê duyệt</span>
          </button>

          <button
            type="button"
            :disabled="saving"
            class="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-navy transition-colors duration-150 hover:border-amber/60 hover:bg-amber/5 disabled:opacity-60"
            @click="startAction('requestChanges')"
          >
            <AlertTriangle :size="15" class="text-amber" aria-hidden="true" />
            <span>Yêu cầu chỉnh sửa</span>
          </button>

          <button
            type="button"
            :disabled="saving"
            class="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-danger transition-colors duration-150 hover:border-danger/40 hover:bg-danger/5 disabled:opacity-60"
            @click="startAction('reject')"
          >
            <XCircle :size="15" aria-hidden="true" />
            <span>Từ chối</span>
          </button>
        </div>

        <p v-else class="rounded-xl bg-subtle/80 px-3.5 py-3 text-xs text-slate-600">
          {{ isCourse ? 'Khóa học' : 'Tài liệu' }} này đã được xử lý và ghi nhận kết luận.
        </p>
      </aside>
    </div>

    <ReviewActionModal
      :open="actionModalOpen"
      :action="selectedAction"
      :item-title="item?.title"
      :item-description="item?.description"
      :saving="saving"
      :error-message="actionError"
      :item-kind="isCourse ? 'Khóa học' : 'Tài liệu'"
      @close="actionModalOpen = false"
      @confirm="confirmAction"
    />
  </div>
</template>
