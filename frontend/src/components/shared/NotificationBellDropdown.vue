<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Bell, CheckCheck, ExternalLink } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import {
  extractApiError,
  fetchNotifications,
  fetchUnreadNotificationCount,
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
const open = ref(false)
const rootRef = ref(null)
const unreadCount = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref('')
const busyAll = ref(false)

const allRouteName = computed(() =>
  props.role === 'EXPERT' ? 'reviewer-notifications' : 'admin-notifications',
)

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
  return { name: allRouteName.value }
}

async function refreshCount() {
  try {
    unreadCount.value = await fetchUnreadNotificationCount()
  } catch {
    // Silent background count refresh failure
  }
}

async function loadDropdown() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchNotifications({ limit: 6, offset: 0 })
    items.value = Array.isArray(res?.items) ? res.items : []
    unreadCount.value = Number(res?.unreadCount || 0)
  } catch (err) {
    error.value = extractApiError(err, 'Không thể tải danh sách thông báo.')
  } finally {
    loading.value = false
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    loadDropdown()
  }
}

async function openItem(item) {
  if (!item.daDoc) {
    try {
      await markNotificationRead(item.maThongBao)
      item.daDoc = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // ignore if already read
    }
  }
  open.value = false
  router.push(resolveTargetRoute(item))
}

async function markAll() {
  if (busyAll.value || unreadCount.value === 0) return
  busyAll.value = true
  try {
    await markAllNotificationsRead()
    items.value = items.value.map((n) => ({ ...n, daDoc: true }))
    unreadCount.value = 0
  } catch (err) {
    error.value = extractApiError(err, 'Không thể đánh dấu tất cả đã đọc.')
  } finally {
    busyAll.value = false
  }
}

function handlePointerDown(event) {
  if (open.value && rootRef.value && !rootRef.value.contains(event.target)) {
    open.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape' && open.value) {
    open.value = false
  }
}

let pollTimer = null

onMounted(() => {
  refreshCount()
  pollTimer = window.setInterval(refreshCount, 45000)
  document.addEventListener('pointerdown', handlePointerDown)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  if (pollTimer) window.clearInterval(pollTimer)
  document.removeEventListener('pointerdown', handlePointerDown)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div ref="rootRef" class="relative shrink-0">
    <button
      type="button"
      class="relative flex size-9 items-center justify-center rounded-lg border border-transparent text-slate-600 transition-colors duration-150 hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
      :aria-label="unreadCount > 0 ? `Thông báo (${unreadCount} chưa đọc)` : 'Thông báo'"
      :aria-expanded="open"
      @click="toggle"
    >
      <Bell :size="18" aria-hidden="true" />
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex min-w-[18px] items-center justify-center rounded-full bg-amber px-1 text-[10px] font-bold leading-[18px] text-white tabular-nums"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <Transition name="es-popover">
      <div
        v-if="open"
        class="absolute right-0 top-11 z-50 w-[min(92vw,380px)] origin-top-right rounded-xl border border-border bg-surface shadow-xl"
        role="dialog"
        aria-label="Thông báo gần đây"
      >
        <div class="flex items-center justify-between border-b border-border/80 px-4 py-3">
          <div>
            <p class="text-sm font-bold text-navy">Thông báo</p>
            <p class="text-xs text-muted">{{ unreadCount }} chưa đọc</p>
          </div>
          <button
            v-if="unreadCount > 0"
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-teal transition-colors hover:bg-subtle disabled:opacity-50"
            :disabled="busyAll"
            @click="markAll"
          >
            <CheckCheck :size="14" aria-hidden="true" />
            <span>Đọc tất cả</span>
          </button>
        </div>

        <div class="max-h-80 overflow-y-auto divide-y divide-border/70">
          <div v-if="loading" class="space-y-3 p-4">
            <div v-for="i in 3" :key="i" class="es-skeleton h-12 w-full rounded-lg" />
          </div>

          <p v-else-if="error" class="p-4 text-xs text-danger" role="alert">
            {{ error }}
          </p>

          <p v-else-if="items.length === 0" class="px-4 py-8 text-center text-xs text-muted">
            Chưa có thông báo nào.
          </p>

          <button
            v-for="item in items"
            v-else
            :key="item.maThongBao"
            type="button"
            class="flex w-full items-start gap-2.5 px-4 py-3 text-left transition-colors hover:bg-subtle/70 focus-visible:bg-subtle focus-visible:outline-none"
            :class="item.daDoc ? 'bg-surface' : 'bg-teal/[0.04]'"
            @click="openItem(item)"
          >
            <span
              class="mt-1.5 size-2 shrink-0 rounded-full"
              :class="item.daDoc ? 'bg-slate-300' : 'bg-teal'"
              aria-hidden="true"
            />
            <div class="min-w-0 flex-1">
              <p class="truncate text-xs font-semibold text-navy">{{ item.tieuDe }}</p>
              <p class="mt-0.5 line-clamp-2 text-xs leading-relaxed text-muted">{{ item.noiDung }}</p>
              <p class="mt-1 text-[11px] text-slate-400 tabular-nums">{{ formatDateTimeVi(item.ngayTao) }}</p>
            </div>
          </button>
        </div>

        <div class="border-t border-border/80 px-3 py-2">
          <RouterLink
            :to="{ name: allRouteName }"
            class="flex items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-semibold text-navy transition-colors hover:bg-subtle"
            @click="open = false"
          >
            <span>Xem tất cả thông báo</span>
            <ExternalLink :size="13" aria-hidden="true" />
          </RouterLink>
        </div>
      </div>
    </Transition>
  </div>
</template>
