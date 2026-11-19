<script setup>
import { computed, ref } from 'vue'
import { Bell, ChevronDown, Menu, UserRound } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { getAdminDashboardStats, getAdminProfile } from '@/service/adminService'

const emit = defineEmits(['toggle-navigation'])

const route = useRoute()
const accountOpen = ref(false)
const notificationsOpen = ref(false)
const title = computed(() => route.meta.title || 'Dashboard')
const section = computed(() => route.meta.adminSection || 'Quản trị hệ thống')
const stats = computed(() => getAdminDashboardStats())
const profile = computed(() => getAdminProfile())
const initials = computed(() => {
  const words = profile.value.fullName.trim().split(/\s+/).filter(Boolean)
  if (!words.length) return 'AD'
  return words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`.toLocaleUpperCase('vi')
    : words[0].slice(0, 2).toLocaleUpperCase('vi')
})
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
    <div class="flex min-h-[72px] items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
      <div class="flex min-w-0 items-center gap-3">
        <button type="button" class="flex size-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-navy hover:bg-background lg:hidden" aria-label="Mở điều hướng quản trị" @click="emit('toggle-navigation')">
          <Menu :size="19" aria-hidden="true" />
        </button>
        <div class="min-w-0">
          <p class="truncate text-xs text-muted"><RouterLink :to="{ name: 'admin-dashboard' }" class="hover:text-primary">Admin</RouterLink> / {{ section }}</p>
          <h1 class="mt-1 truncate text-lg font-bold text-navy sm:text-xl">{{ title }}</h1>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2 sm:gap-3">
        <div class="relative">
          <button type="button" class="relative flex size-10 items-center justify-center rounded-xl text-muted hover:bg-background hover:text-navy" aria-label="Thông báo quản trị" :aria-expanded="notificationsOpen" @click="notificationsOpen = !notificationsOpen; accountOpen = false">
            <Bell :size="19" aria-hidden="true" />
            <span v-if="stats.reviewQueue" class="absolute right-2 top-2 size-2 rounded-full bg-primary" aria-label="Có nội dung cần theo dõi"></span>
          </button>
          <div v-if="notificationsOpen" class="absolute right-0 top-12 z-40 w-[min(88vw,320px)] rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
            <p class="font-semibold text-navy">Thông báo hệ thống</p>
            <p class="mt-2 text-sm leading-6 text-muted">{{ stats.unassigned }} nội dung đang chờ phân công Reviewer.</p>
            <RouterLink :to="{ name: 'admin-assign-reviewer' }" class="mt-3 inline-flex text-sm font-semibold text-primary hover:underline" @click="notificationsOpen = false">
              Mở phân công
            </RouterLink>
          </div>
        </div>

        <div class="relative">
          <button type="button" class="flex items-center gap-2 rounded-xl p-1.5 text-left hover:bg-background" aria-label="Menu tài khoản Admin" :aria-expanded="accountOpen" @click="accountOpen = !accountOpen; notificationsOpen = false">
            <span class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{{ initials }}</span>
            <span class="hidden min-w-0 sm:block">
              <span class="block max-w-36 truncate text-sm font-semibold text-navy">{{ profile.fullName }}</span>
              <span class="block text-xs text-muted">Quản trị viên</span>
            </span>
            <ChevronDown class="hidden text-muted sm:block" :size="15" aria-hidden="true" />
          </button>
          <div v-if="accountOpen" class="absolute right-0 top-12 z-40 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
            <RouterLink :to="{ name: 'admin-profile' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false">
              <UserRound :size="16" aria-hidden="true" /> Thông tin cá nhân
            </RouterLink>
            <button type="button" disabled title="Chưa tích hợp xác thực" class="mt-1 w-full cursor-not-allowed rounded-lg px-3 py-2 text-left text-sm text-muted/70">
              Đăng xuất · chưa tích hợp
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
