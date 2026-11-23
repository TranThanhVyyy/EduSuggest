<script setup>
import { computed } from 'vue'
import { ChevronDown, LogOut } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { authState } from '@/service/authState'
import { logoutAccount } from '@/service/authService'

const logoutError = ref('')
const router = useRouter()
const fullName = computed(() => authState.user?.hoTen || authState.user?.tenTaiKhoan || 'Chuyên gia')

async function logout() {
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
  <header class="relative z-10 flex min-h-20 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-7">
    <div class="min-w-0">
      <p class="hidden text-xs font-medium text-muted sm:block">EduSuggest / Người kiểm duyệt</p>
      <h1 class="truncate text-lg font-bold tracking-tight text-navy sm:mt-1 sm:text-xl">
        {{ $route.meta.title || 'Không gian kiểm duyệt' }}
      </h1>
    </div>

    <div class="flex shrink-0 items-center gap-2 sm:gap-4">
      <RouterLink :to="{ name: 'reviewer-profile' }" class="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-background focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
        <span class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
          {{ fullName.split(' ').slice(-1)[0].slice(0, 1) }}
        </span>
        <span class="hidden text-left sm:block">
          <span class="block max-w-36 truncate text-sm font-semibold text-navy">{{ fullName }}</span>
          <span class="block text-xs text-muted">Người kiểm duyệt</span>
        </span>
        <ChevronDown class="hidden text-muted sm:block" :size="15" aria-hidden="true" />
        <span class="sr-only">Mở hồ sơ cá nhân</span>
      </RouterLink>
      <button type="button" class="flex size-10 items-center justify-center rounded-xl text-muted hover:bg-background hover:text-primary" aria-label="Đăng xuất" @click="logout">
        <LogOut :size="18" aria-hidden="true" />
      </button>
    </div>
    <p v-if="logoutError" class="px-4 pb-3 text-xs text-primary" role="status">{{ logoutError }}</p>
  </header>
</template>
