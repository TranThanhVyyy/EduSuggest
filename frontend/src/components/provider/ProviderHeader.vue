<script setup>
import { computed, ref } from 'vue'
import { Bell, ChevronDown, LogOut, Menu, UserRound } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { authState } from '@/service/authState'
import { logoutAccount } from '@/service/authService'

const emit = defineEmits(['toggle-navigation'])
const route = useRoute()
const router = useRouter()
const notificationsOpen = ref(false)
const accountOpen = ref(false)
const logoutError = ref('')
const title = computed(() => route.meta.title || 'Dashboard')
const notifications = ref([])
const fullName = computed(() => authState.user?.hoTen || '')
const initials = computed(() => {
  const words = fullName.value.trim().split(/\s+/).filter(Boolean)
  return words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`.toLocaleUpperCase('vi')
    : words[0]?.slice(0, 2).toLocaleUpperCase('vi') || 'PR'
})

async function logout() {
  accountOpen.value = false
  logoutError.value = ''
  try {
    await logoutAccount()
  } catch {
    logoutError.value = 'Không thể xác nhận đăng xuất trên Backend; phiên cục bộ đã được xóa.'
  }
  await router.replace({ name: 'login' })
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
    <div class="flex min-h-[72px] items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
      <div class="flex min-w-0 items-center gap-3">
        <button type="button" class="flex size-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-navy hover:bg-background lg:hidden" aria-label="Mở điều hướng Provider" @click="emit('toggle-navigation')">
          <Menu :size="19" aria-hidden="true" />
        </button>
        <div class="min-w-0">
          <p class="truncate text-xs text-muted"><RouterLink :to="{ name: 'provider-dashboard' }" class="hover:text-primary">Provider</RouterLink> / Không gian quản lý</p>
          <h1 class="mt-1 truncate text-lg font-bold text-navy sm:text-xl">{{ title }}</h1>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2 sm:gap-3">
        <div class="relative">
          <button type="button" class="relative flex size-10 items-center justify-center rounded-xl text-muted hover:bg-background hover:text-navy" aria-label="Thông báo Provider" :aria-expanded="notificationsOpen" @click="notificationsOpen = !notificationsOpen; accountOpen = false">
            <Bell :size="19" aria-hidden="true" />
            <span v-if="notifications.length" class="absolute right-2 top-2 size-2 rounded-full bg-accent" aria-label="Có thông báo"></span>
          </button>
          <div v-if="notificationsOpen" class="absolute right-0 top-12 z-40 w-[min(88vw,340px)] rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
            <p class="font-semibold text-navy">Thông báo kiểm duyệt</p>
            <ul v-if="notifications.length" class="mt-2 divide-y divide-slate-100">
              <li v-for="notification in notifications" :key="notification.id" class="py-2.5">
                <p class="text-sm font-semibold text-navy">{{ notification.title }}</p>
                <p class="mt-0.5 text-xs text-muted">{{ notification.detail }}</p>
              </li>
            </ul>
            <p v-else class="mt-2 text-sm text-muted">Backend hiện chưa cung cấp API thông báo Provider.</p>
          </div>
        </div>

        <div class="relative">
          <button type="button" class="flex items-center gap-2 rounded-xl p-1.5 text-left hover:bg-background" aria-label="Menu tài khoản Provider" :aria-expanded="accountOpen" @click="accountOpen = !accountOpen; notificationsOpen = false">
            <span class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{{ initials }}</span>
            <span class="hidden min-w-0 sm:block">
              <span class="block max-w-36 truncate text-sm font-semibold text-navy">{{ fullName }}</span>
              <span class="block text-xs text-muted">Nhà cung cấp</span>
            </span>
            <ChevronDown class="hidden text-muted sm:block" :size="15" aria-hidden="true" />
          </button>
          <div v-if="accountOpen" class="absolute right-0 top-12 z-40 w-60 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
            <RouterLink :to="{ name: 'provider-profile' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false">
              <UserRound :size="16" aria-hidden="true" /> Hồ sơ cá nhân
            </RouterLink>
            <button type="button" class="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-muted hover:bg-background" @click="logout">
              <LogOut :size="16" aria-hidden="true" /> Đăng xuất
            </button>
          </div>
        </div>
      </div>
    </div>
    <p v-if="logoutError" class="px-4 pb-3 text-xs text-primary" role="status">{{ logoutError }}</p>
  </header>
</template>
