<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronDown, ChevronRight, LogOut, Menu, UserRound } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { authState } from '@/service/authState'
import { logoutAccount } from '@/service/authService'
import NotificationBellDropdown from '@/components/shared/NotificationBellDropdown.vue'

const emit = defineEmits(['toggle-navigation'])
const route = useRoute()
const router = useRouter()

const accountOpen = ref(false)
const accountRef = ref(null)
const logoutError = ref('')

const pageTitle = computed(() => route.meta.title || 'Tổng quan kiểm duyệt')
const fullName = computed(() => authState.user?.hoTen || authState.user?.tenTaiKhoan || 'Chuyên gia')
const initials = computed(() => {
  const words = fullName.value.trim().split(/\s+/).filter(Boolean)
  return words.length > 1
    ? `${words[0][0]}${words[words.length - 1][0]}`.toLocaleUpperCase('vi')
    : words[0]?.slice(0, 2).toLocaleUpperCase('vi') || 'CG'
})

function handlePointerDown(event) {
  if (accountOpen.value && accountRef.value && !accountRef.value.contains(event.target)) {
    accountOpen.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
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
          aria-label="Mở điều hướng Chuyên gia"
          @click="emit('toggle-navigation')"
        >
          <Menu :size="18" aria-hidden="true" />
        </button>

        <nav class="flex min-w-0 items-center gap-1.5 text-sm" aria-label="Vị trí hiện tại">
          <RouterLink
            :to="{ name: 'reviewer-dashboard' }"
            class="shrink-0 font-medium text-slate-500 transition-colors duration-150 hover:text-navy"
          >
            Chuyên gia
          </RouterLink>
          <ChevronRight :size="14" class="shrink-0 text-slate-400" aria-hidden="true" />
          <span class="truncate font-semibold text-navy">{{ pageTitle }}</span>
        </nav>
      </div>

      <!-- Right: Notification Bell + Compact Account Pill -->
      <div class="flex items-center gap-2 shrink-0">
        <NotificationBellDropdown role="EXPERT" />
        <div ref="accountRef" class="relative shrink-0">
        <button
          type="button"
          class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors duration-150 hover:bg-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
          aria-label="Menu tài khoản Chuyên gia"
          :aria-expanded="accountOpen"
          @click="accountOpen = !accountOpen"
        >
          <span class="flex size-7 items-center justify-center rounded-full bg-navy text-[11px] font-bold text-white">
            {{ initials }}
          </span>
          <span class="hidden max-w-40 truncate text-sm font-medium text-navy sm:block">
            {{ fullName }}
          </span>
          <ChevronDown class="hidden text-slate-400 sm:block" :size="14" aria-hidden="true" />
        </button>

        <Transition name="es-popover">
          <div
            v-if="accountOpen"
            class="absolute right-0 top-11 z-40 w-56 origin-top-right rounded-xl border border-border bg-surface p-1.5 shadow-lg"
          >
            <div class="mb-1 border-b border-border/70 px-3 py-2">
              <p class="truncate text-sm font-semibold text-navy">{{ fullName }}</p>
              <p class="text-xs text-slate-500">Chuyên gia kiểm duyệt</p>
            </div>
            <RouterLink
              :to="{ name: 'reviewer-profile' }"
              class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
              @click="accountOpen = false"
            >
              <UserRound :size="15" class="text-slate-500" aria-hidden="true" />
              <span>Hồ sơ chuyên gia</span>
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
