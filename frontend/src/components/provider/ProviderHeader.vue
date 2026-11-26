<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Bell, ChevronDown, ChevronRight, LogOut, Menu, UserRound } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { authState } from '@/service/authState'
import { logoutAccount } from '@/service/authService'

const emit = defineEmits(['toggle-navigation'])
const route = useRoute()
const router = useRouter()

const notificationsOpen = ref(false)
const accountOpen = ref(false)
const notificationsRef = ref(null)
const accountRef = ref(null)
const logoutError = ref('')

const pageTitle = computed(() => route.meta.title || 'Tổng quan')
const notifications = ref([])
const fullName = computed(() => authState.user?.hoTen || 'Nhà cung cấp')
const initials = computed(() => {
  const words = fullName.value.trim().split(/\s+/).filter(Boolean)
  return words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`.toLocaleUpperCase('vi')
    : words[0]?.slice(0, 2).toLocaleUpperCase('vi') || 'PR'
})

function handlePointerDown(event) {
  if (notificationsOpen.value && notificationsRef.value && !notificationsRef.value.contains(event.target)) {
    notificationsOpen.value = false
  }
  if (accountOpen.value && accountRef.value && !accountRef.value.contains(event.target)) {
    accountOpen.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    notificationsOpen.value = false
    accountOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handlePointerDown)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handlePointerDown)
  document.removeEventListener('keydown', handleKeydown)
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
  <header class="sticky top-0 z-30 border-b border-border/80 bg-surface/90 backdrop-blur-md">
    <div class="flex h-15 items-center justify-between gap-3 px-4 sm:px-6 lg:px-10">
      <!-- Left: Mobile trigger + Compact Breadcrumb -->
      <div class="flex min-w-0 items-center gap-2.5">
        <button
          type="button"
          class="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border text-navy transition-colors duration-150 hover:bg-subtle lg:hidden"
          aria-label="Mở điều hướng Provider"
          @click="emit('toggle-navigation')"
        >
          <Menu :size="18" aria-hidden="true" />
        </button>

        <nav class="flex min-w-0 items-center gap-1.5 text-sm" aria-label="Vị trí hiện tại">
          <RouterLink
            :to="{ name: 'provider-dashboard' }"
            class="shrink-0 font-medium text-slate-500 transition-colors duration-150 hover:text-navy"
          >
            Nhà cung cấp
          </RouterLink>
          <ChevronRight :size="14" class="shrink-0 text-slate-400" aria-hidden="true" />
          <span class="truncate font-semibold text-navy">{{ pageTitle }}</span>
        </nav>
      </div>

      <!-- Right: Notifications + Compact Account Pill -->
      <div class="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <div ref="notificationsRef" class="relative">
          <button
            type="button"
            class="relative flex size-9 items-center justify-center rounded-lg text-slate-500 transition-colors duration-150 hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            aria-label="Thông báo kiểm duyệt"
            :aria-expanded="notificationsOpen"
            @click="notificationsOpen = !notificationsOpen; accountOpen = false"
          >
            <Bell :size="18" aria-hidden="true" />
            <span
              v-if="notifications.length"
              class="absolute right-2 top-2 size-1.5 rounded-full bg-amber"
              aria-label="Có thông báo mới"
            ></span>
          </button>

          <Transition name="es-popover">
            <div
              v-if="notificationsOpen"
              class="absolute right-0 top-11 z-40 w-[min(88vw,320px)] origin-top-right rounded-xl border border-border bg-surface p-4 shadow-lg"
            >
              <p class="text-sm font-semibold text-navy">Thông báo kiểm duyệt</p>
              <ul v-if="notifications.length" class="mt-2.5 divide-y divide-border/60">
                <li v-for="notification in notifications" :key="notification.id" class="py-2.5">
                  <p class="text-sm font-medium text-navy">{{ notification.title }}</p>
                  <p class="mt-0.5 text-xs text-slate-600">{{ notification.detail }}</p>
                </li>
              </ul>
              <p v-else class="mt-2 text-xs leading-relaxed text-slate-500">
                Chưa có thông báo mới. Phản hồi từ Chuyên gia kiểm duyệt sẽ hiển thị tại đây.
              </p>
            </div>
          </Transition>
        </div>

        <div class="h-5 w-px bg-border/80 hidden sm:block" aria-hidden="true"></div>

        <div ref="accountRef" class="relative">
          <button
            type="button"
            class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors duration-150 hover:bg-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            aria-label="Menu tài khoản Provider"
            :aria-expanded="accountOpen"
            @click="accountOpen = !accountOpen; notificationsOpen = false"
          >
            <span class="flex size-7 items-center justify-center rounded-full bg-navy text-[11px] font-bold text-white">
              {{ initials }}
            </span>
            <span class="hidden max-w-36 truncate text-sm font-medium text-navy sm:block">
              {{ fullName }}
            </span>
            <ChevronDown class="hidden text-slate-400 sm:block" :size="14" aria-hidden="true" />
          </button>

          <Transition name="es-popover">
            <div
              v-if="accountOpen"
              class="absolute right-0 top-11 z-40 w-56 origin-top-right rounded-xl border border-border bg-surface p-1.5 shadow-lg"
            >
              <div class="border-b border-border/70 px-3 py-2 mb-1">
                <p class="truncate text-sm font-semibold text-navy">{{ fullName }}</p>
                <p class="text-xs text-slate-500">Nhà cung cấp khóa học</p>
              </div>
              <RouterLink
                :to="{ name: 'provider-profile' }"
                class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                @click="accountOpen = false"
              >
                <UserRound :size="15" class="text-slate-500" aria-hidden="true" />
                <span>Hồ sơ cá nhân</span>
              </RouterLink>
              <button
                type="button"
                class="mt-0.5 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-600 transition-colors duration-150 hover:bg-subtle hover:text-navy"
                @click="logout"
              >
                <LogOut :size="15" class="text-slate-500" aria-hidden="true" />
                <span>Đăng xuất</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <p v-if="logoutError" class="border-t border-border/70 bg-subtle/60 px-4 py-2 text-xs text-navy sm:px-6 lg:px-10" role="status">
      {{ logoutError }}
    </p>
  </header>
</template>
