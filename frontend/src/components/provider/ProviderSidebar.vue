<script setup>
import { computed } from 'vue'
import {
  BookOpen,
  BookPlus,
  ClipboardList,
  GraduationCap,
  History,
  LayoutDashboard,
  LogOut,
  UserRound,
  X,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { PROVIDER_STATUS, getProviderDashboardData } from '@/service/providerService'

defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-collapse', 'close-mobile'])
const route = useRoute()
const stats = computed(() => getProviderDashboardData())
const courseLinks = [
  { label: 'Tất cả khóa học', routeName: 'provider-courses', icon: BookOpen },
  { label: 'Tạo khóa học mới', routeName: 'provider-course-create', icon: BookPlus },
  { label: 'Bản nháp', routeName: 'provider-courses', query: { status: PROVIDER_STATUS.draft } },
  { label: 'Chờ kiểm duyệt', routeName: 'provider-courses', query: { status: PROVIDER_STATUS.pending } },
  { label: 'Đã phê duyệt', routeName: 'provider-courses', query: { status: PROVIDER_STATUS.approved } },
  { label: 'Từ chối / chỉnh sửa', routeName: 'provider-courses', query: { status: 'feedback' } },
]
const reviewLinks = [
  { label: 'Theo dõi kiểm duyệt', routeName: 'provider-reviews', icon: ClipboardList },
  { label: 'Lịch sử kiểm duyệt', routeName: 'provider-review-history', icon: History },
]

function isActive(link) {
  if (route.name !== link.routeName) return false
  if (!link.query) return !route.query.status
  return Object.entries(link.query).every(([key, value]) => route.query[key] === value)
}

function renderLinks() {
  return [
    { label: 'Dashboard', routeName: 'provider-dashboard', icon: LayoutDashboard },
    ...courseLinks,
    ...reviewLinks,
    { label: 'Hồ sơ cá nhân', routeName: 'provider-profile', icon: UserRound },
  ]
}

const allLinks = renderLinks()
</script>

<template>
  <aside class="sticky top-0 hidden h-screen shrink-0 flex-col overflow-y-auto bg-navy px-3 py-5 text-white transition-[width] duration-200 lg:flex" :class="collapsed ? 'w-20' : 'w-[270px]'">
    <div class="flex items-center justify-between gap-2 px-1">
      <RouterLink :to="{ name: 'provider-dashboard' }" class="flex min-w-0 items-center gap-2.5" aria-label="EduSuggest Course Provider">
        <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white">
          <GraduationCap :size="21" aria-hidden="true" />
        </span>
        <span v-if="!collapsed" class="min-w-0">
          <span class="block truncate text-base font-bold">EduSuggest</span>
          <span class="block text-[10px] font-semibold tracking-[0.14em] text-white/55">COURSE PROVIDER</span>
        </span>
      </RouterLink>
      <button v-if="!collapsed" type="button" class="flex size-8 shrink-0 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white" aria-label="Thu gọn thanh điều hướng" @click="emit('toggle-collapse')">
        <BookOpen :size="17" aria-hidden="true" />
      </button>
    </div>
    <button v-if="collapsed" type="button" class="mx-auto mt-3 flex size-9 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white" aria-label="Mở rộng thanh điều hướng" @click="emit('toggle-collapse')">
      <BookOpen :size="17" aria-hidden="true" />
    </button>

    <nav class="mt-7 flex-1 space-y-5" aria-label="Điều hướng người cung cấp khóa học">
      <section>
        <p v-if="!collapsed" class="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/45">Không gian của tôi</p>
        <div class="space-y-1">
          <RouterLink
            v-for="link in allLinks"
            :key="`${link.routeName}-${link.label}`"
            :to="{ name: link.routeName, query: link.query }"
            class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            :class="isActive(link) ? 'bg-primary font-semibold text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'"
            :title="collapsed ? link.label : undefined"
            :aria-current="isActive(link) ? 'page' : undefined"
            @click="emit('close-mobile')"
          >
            <component :is="link.icon || ClipboardList" class="shrink-0" :size="18" aria-hidden="true" />
            <span v-if="!collapsed" class="min-w-0 flex-1 truncate">{{ link.label }}</span>
            <span v-if="!collapsed && link.label === 'Chờ kiểm duyệt' && stats.statusCounts[PROVIDER_STATUS.pending]" class="rounded-full bg-white/15 px-2 py-0.5 text-[10px]">
              {{ stats.statusCounts[PROVIDER_STATUS.pending] }}
            </span>
          </RouterLink>
        </div>
      </section>
    </nav>

    <div v-if="!collapsed" class="mt-5 rounded-xl border border-white/10 bg-white/5 p-3">
      <p class="text-xs font-semibold">Bản xem trước</p>
      <p class="mt-1 text-[11px] leading-5 text-white/55">Dữ liệu mock trong bộ nhớ; chưa có xác thực hoặc đồng bộ Backend.</p>
    </div>
    <button v-if="!collapsed" type="button" disabled title="Chưa tích hợp xác thực" class="mt-3 flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-white/40">
      <LogOut :size="18" aria-hidden="true" /> Đăng xuất · chưa tích hợp
    </button>
  </aside>

  <div v-if="mobileOpen" class="fixed inset-0 z-50 lg:hidden">
    <button type="button" class="absolute inset-0 bg-navy/55" aria-label="Đóng menu" @click="emit('close-mobile')"></button>
    <aside class="relative flex h-full w-[min(86vw,320px)] flex-col overflow-y-auto bg-navy px-3 py-5 text-white shadow-xl">
      <div class="flex items-center justify-between gap-3 px-1">
        <RouterLink :to="{ name: 'provider-dashboard' }" class="flex items-center gap-2.5" @click="emit('close-mobile')">
          <span class="flex size-10 items-center justify-center rounded-xl bg-primary text-white"><GraduationCap :size="21" aria-hidden="true" /></span>
          <span><span class="block text-base font-bold">EduSuggest</span><span class="block text-[10px] font-semibold tracking-[0.14em] text-white/55">COURSE PROVIDER</span></span>
        </RouterLink>
        <button type="button" class="flex size-9 items-center justify-center rounded-lg text-white/70 hover:bg-white/10" aria-label="Đóng menu" @click="emit('close-mobile')"><X :size="19" aria-hidden="true" /></button>
      </div>
      <nav class="mt-7 flex-1 space-y-1" aria-label="Điều hướng Provider di động">
        <RouterLink
          v-for="link in allLinks"
          :key="`mobile-${link.routeName}-${link.label}`"
          :to="{ name: link.routeName, query: link.query }"
          class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm"
          :class="isActive(link) ? 'bg-primary font-semibold text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'"
          @click="emit('close-mobile')"
        >
          <component :is="link.icon || ClipboardList" :size="18" aria-hidden="true" />
          <span class="truncate">{{ link.label }}</span>
        </RouterLink>
      </nav>
      <p class="mt-5 rounded-xl border border-white/10 bg-white/5 p-3 text-xs leading-5 text-white/55">Demo mock; xác thực và đồng bộ Backend chưa được tích hợp.</p>
    </aside>
  </div>
</template>
