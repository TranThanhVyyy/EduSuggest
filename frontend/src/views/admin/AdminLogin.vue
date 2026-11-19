<script setup>
import { KeyRound } from 'lucide-vue-next'
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-background p-4">
    <section class="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-8">
      <span class="mx-auto flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <KeyRound :size="22" aria-hidden="true" />
      </span>
      <p class="mt-4 text-sm font-semibold text-primary">EduSuggest · Admin</p>
      <h1 class="mt-2 text-2xl font-bold text-navy">Đăng nhập quản trị</h1>
      <div class="mt-5 rounded-xl border border-slate-200 bg-background p-4 text-left text-sm leading-6 text-muted">
        Chức năng xác thực chưa được tích hợp. Dự án hiện không có API đăng nhập hoặc phân quyền Admin; vì vậy trang này không thu thập thông tin đăng nhập và không giả lập đăng nhập thành công.
      </div>
      <RouterLink :to="{ name: 'home' }" class="mt-5 inline-flex rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">
        Quay lại trang chủ
      </RouterLink>
    </section>
  </main>
</template>
