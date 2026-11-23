<script setup>
import { computed } from 'vue'
import { authState } from '@/service/authState'
import { getRoleName } from '@/service/authService'

const roleTitles = {
  ADMIN: 'Quản trị viên',
  EXPERT: 'Chuyên gia',
  PROVIDER: 'Nhà cung cấp',
  USER: 'Người học',
}
const roleTitle = computed(() => roleTitles[getRoleName()] || 'Tài khoản')
const userName = computed(() => authState.user?.hoTen || authState.user?.email || '')
</script>

<template>
  <main class="mx-auto flex min-h-[65vh] max-w-3xl items-center px-4 py-12 sm:px-6">
    <section class="w-full rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-10">
      <p class="text-xs font-semibold uppercase tracking-wider text-primary">Không gian EduSuggest</p>
      <h1 class="mt-3 text-3xl font-bold text-navy">Xin chào{{ userName ? `, ${userName}` : '' }}!</h1>
      <p class="mt-3 text-base leading-7 text-muted">
        Bạn đang đăng nhập với vai trò <strong class="text-navy">{{ roleTitle }}</strong>.
      </p>
      <div class="mt-7 rounded-2xl border border-slate-200 bg-background p-5">
        <h2 class="font-semibold text-navy">Khu vực nghiệp vụ</h2>
        
      </div>
    </section>
  </main>
</template>
