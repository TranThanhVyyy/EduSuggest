<script setup>
import { computed } from 'vue'
import { ArrowRight } from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()
const isRegister = computed(() => route.name === 'provider-register')
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-background p-5">
    <section class="w-full max-w-md border-y border-border py-8">
      <p class="ui-eyebrow">EduSuggest · Tài khoản</p>
      <h1 class="ui-page-title mt-3">{{ isRegister ? 'Tạo tài khoản' : 'Đăng nhập' }}</h1>
      <p class="mt-3 text-sm leading-6 text-muted">Đăng nhập và đăng ký dùng chung hệ thống tài khoản. Vai trò nhà cung cấp được cấp sau khi hồ sơ được duyệt.</p>
      <RouterLink :to="{ name: isRegister ? 'register' : 'login' }" class="mt-6 inline-flex items-center gap-2 font-medium text-secondary hover:underline">{{ isRegister ? 'Mở đăng ký tài khoản' : 'Mở đăng nhập' }} <ArrowRight :size="16" aria-hidden="true" /></RouterLink>
      <p class="mt-6 border-t border-border pt-4 text-sm text-muted">Đã có tài khoản Provider? <RouterLink :to="{ name: 'provider-dashboard' }" class="font-medium text-secondary hover:underline">Vào khu vực của bạn</RouterLink></p>
    </section>
  </main>
</template>
