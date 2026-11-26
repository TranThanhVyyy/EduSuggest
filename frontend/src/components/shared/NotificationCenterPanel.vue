<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Bell, Check, CheckCheck, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import {
  extractApiError,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/service/notificationApiService'
import { formatDateTimeVi } from '@/service/adminPhase3ApiService'

const props = defineProps({
  role: {
    type: String,
    default: 'ADMIN',
  },
})

const router = useRouter()
const filterTab = ref('all') // 'all' | 'unread' | 'read'
const limit = 20
const offset = ref(0)
const total = ref(0)
const unreadCount = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref('')
const feedback = ref('')
const busyId = ref(null)
const busyAll = ref(false)

const currentPage = computed(() => Math.floor(offset.value / limit) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

function resolveTargetRoute(item) {
  const type = String(item?.loaiThongBao || '').toUpperCase()
  if (props.role === 'ADMIN') {
    if (type.startsWith('AVAILABILITY_')) return { name: 'admin-availability' }
    if (type.startsWith('ACCOUNTABILITY_') || type.includes('VIOLATION') || type.includes('LOCK')) {
      return { name: 'admin-accountability' }
    }
    if (type.startsWith('ASSIGNMENT_') || type.includes('QUEUE') || type.includes('REASSIGN')) {
      return { name: 'admin-assign-reviewer' }
    }
  } else if (props.role === 'EXPERT') {
    const pcId = item?.duLieuLienKet?.maPhanCong
    if (type.startsWith('ASSIGNMENT_') && pcId) {
      return { name: 'reviewer-assignment-detail', params: { assignmentId: String(pcId) } }
    }
    if (type.startsWith('ASSIGNMENT_')) return { name: 'reviewer-assignments' }
    if (type.startsWith('AVAILABILITY_')) return { name: 'reviewer-availability' }
    if (type.startsWith('ACCOUNTABILITY_') || type.includes('VIOLATION') || type.includes('LOCK')) {
      return { name: 'reviewer-accountability' }
    }
  }
  return null
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const isRead = filterTab.value === 'all' ? null : filterTab.value === 'read'
    const res = await fetchNotifications({ isRead, limit, offset: offset.value })
    items.value = Array.isArray(res?.items) ? res.items : []
    total.value = Number(res?.total || 0)
    unreadCount.value = Number(res?.unreadCount || 0)
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải trung tâm thông báo.')
  } finally {
    loading.value = false
  }
}

async function handleMarkRead(item) {
  if (item.daDoc || busyId.value === item.maThongBao) return
  busyId.value = item.maThongBao
  feedback.value = ''
  try {
    const updated = await markNotificationRead(item.maThongBao)
    item.daDoc = true
    item.ngayDoc = updated?.ngayDoc || new Date().toISOString()
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (err) {
    error.value = extractApiError(err, 'Không thể đánh dấu đã đọc.')
  } finally {
    busyId.value = null
  }
}

async function handleMarkAllRead() {
  if (busyAll.value || unreadCount.value === 0) return
  busyAll.value = true
  feedback.value = ''
  try {
    const count = await markAllNotificationsRead()
    feedback.value = `Đã đánh dấu ${count} thông báo là đã đọc.`
    await loadData()
  } catch (err) {
    error.value = extractApiError(err, 'Không thể đánh dấu tất cả thông báo đã đọc.')
  } finally {
    busyAll.value = false
  }
}

function navigateToResource(item) {
  const target = resolveTargetRoute(item)
  if (!item.daDoc) handleMarkRead(item)
  if (target) router.push(target)
}

watch(filterTab, () => {
  offset.value = 0
  loadData()
})

onMounted(loadData)
</script>

<template>
  <section class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-teal">Trung tâm thông báo</p>
        <h1 class="mt-1 text-2xl font-bold tracking-tight text-navy">Thông báo hệ thống</h1>
        <p class="mt-1 text-sm text-muted">
          Theo dõi cảnh báo phân công, yêu cầu tạm ngừng và sự kiện kỷ luật theo thời gian thực.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-navy transition-colors hover:bg-subtle"
          :disabled="loading"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
          <span>Làm mới</span>
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-navy/90 disabled:opacity-50"
          :disabled="busyAll || unreadCount === 0"
          @click="handleMarkAllRead"
        >
          <CheckCheck :size="14" aria-hidden="true" />
          <span>Đánh dấu tất cả đã đọc ({{ unreadCount }})</span>
        </button>
      </div>
    </header>

    <UiAlert v-if="error" variant="danger" :message="error" dismissible @dismiss="error = ''" />
    <UiAlert v-if="feedback" variant="success" :message="feedback" dismissible @dismiss="feedback = ''" />

    <!-- Filter Tabs -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="inline-flex rounded-lg border border-border bg-subtle p-1" role="tablist" aria-label="Lọc trạng thái thông báo">
        <button
          v-for="tab in [
            { id: 'all', label: 'Tất cả' },
            { id: 'unread', label: `Chưa đọc (${unreadCount})` },
            { id: 'read', label: 'Đã đọc' },
          ]"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="filterTab === tab.id"
          class="rounded-md px-3 py-1.5 text-xs font-semibold transition-colors"
          :class="filterTab === tab.id ? 'bg-surface text-navy shadow-sm' : 'text-muted hover:text-navy'"
          @click="filterTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <p class="text-xs text-muted tabular-nums">
        Hiển thị {{ items.length }} / {{ total }} thông báo
      </p>
    </div>

    <UiSkeleton v-if="loading" variant="table" :lines="6" />

    <UiEmptyState
      v-else-if="items.length === 0"
      :icon="Bell"
      title="Chưa có thông báo phù hợp"
      :description="filterTab === 'unread' ? 'Bạn đã đọc hết toàn bộ thông báo hiện tại.' : 'Các thông báo mới từ hệ thống sẽ xuất hiện tại đây.'"
    />

    <div v-else class="overflow-hidden rounded-xl border border-border bg-surface divide-y divide-border/80">
      <article
        v-for="item in items"
        :key="item.maThongBao"
        class="flex flex-col gap-3 p-4 transition-colors sm:flex-row sm:items-start sm:justify-between"
        :class="item.daDoc ? 'bg-surface' : 'bg-teal/[0.03]'"
      >
        <div class="min-w-0 flex-1 space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span
              class="size-2 shrink-0 rounded-full"
              :class="item.daDoc ? 'bg-slate-300' : 'bg-teal'"
              aria-hidden="true"
            />
            <h2 class="text-sm font-bold text-navy">{{ item.tieuDe }}</h2>
            <UiStatusBadge
              :tone="item.daDoc ? 'neutral' : 'teal'"
              :label="item.daDoc ? 'Đã đọc' : 'Chưa đọc'"
            />
            <span class="rounded bg-subtle px-1.5 py-0.5 font-mono text-[11px] text-muted">
              {{ item.loaiThongBao }}
            </span>
          </div>
          <p class="text-sm leading-relaxed text-slate-600">{{ item.noiDung }}</p>
          <p class="text-xs text-muted tabular-nums">
            Tạo lúc: {{ formatDateTimeVi(item.ngayTao) }}
            <span v-if="item.ngayDoc"> · Đọc lúc: {{ formatDateTimeVi(item.ngayDoc) }}</span>
          </p>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <button
            v-if="resolveTargetRoute(item)"
            type="button"
            class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy transition-colors hover:bg-subtle"
            @click="navigateToResource(item)"
          >
            Mở liên kết
          </button>
          <button
            v-if="!item.daDoc"
            type="button"
            class="inline-flex items-center gap-1 rounded-lg bg-teal px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-teal-dark disabled:opacity-50"
            :disabled="busyId === item.maThongBao"
            @click="handleMarkRead(item)"
          >
            <Check :size="13" aria-hidden="true" />
            <span>Đã đọc</span>
          </button>
        </div>
      </article>
    </div>

    <!-- Pagination -->
    <div v-if="total > limit" class="flex items-center justify-between border-t border-border pt-4">
      <p class="text-xs text-muted tabular-nums">
        Trang {{ currentPage }} / {{ totalPages }}
      </p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="offset === 0"
          @click="offset = Math.max(0, offset - limit); loadData()"
        >
          <ChevronLeft :size="14" aria-hidden="true" />
          <span>Trước</span>
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy disabled:opacity-40"
          :disabled="offset + limit >= total"
          @click="offset = offset + limit; loadData()"
        >
          <span>Sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </div>
    </div>
  </section>
</template>
