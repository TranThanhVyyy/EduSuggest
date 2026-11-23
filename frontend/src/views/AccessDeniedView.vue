<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { authState } from '@/service/authState'
import { getRoleLandingRouteName, getRoleName } from '@/service/authService'

const isAuthenticated = computed(() => Boolean(authState.accessToken))
const landingRoute = computed(() => {
  const routeName = getRoleLandingRouteName()
  return { name: routeName === 'access-denied' ? 'home' : routeName }
})
const role = computed(() => getRoleName())
</script>

<template>
  <main class="mx-auto flex min-h-[65vh] max-w-2xl items-center px-4 py-12 sm:px-6">
    <section class="w-full rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-10">
      <p class="text-xs font-semibold uppercase tracking-wider text-primary">403 · Không có quyền truy cập</p>
      <h1 class="mt-3 text-2xl font-bold text-navy">Bạn không thể truy cập trang này</h1>
      <p class="mt-3 text-sm leading-6 text-muted">
        {{ role ? `Vai trò ${role} không được cấp quyền cho trang yêu cầu.` : 'Vui lòng đăng nhập bằng tài khoản có quyền phù hợp.' }}
      </p>
      <RouterLink
        :to="isAuthenticated ? landingRoute : { name: 'login' }"
        class="mt-6 inline-flex rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
      >
        {{ isAuthenticated ? 'Về trang của tôi' : 'Đến đăng nhập' }}
      </RouterLink>
    </section>
  </main>
</template>
