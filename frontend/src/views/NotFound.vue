<script setup>
import { RouterLink } from 'vue-router'
import { ArrowLeft, CircleHelp } from 'lucide-vue-next'
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-background px-4 py-12">
    <section class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <span class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <CircleHelp :size="26" aria-hidden="true" />
      </span>
      <p class="mt-5 text-sm font-semibold text-primary">404</p>
      <h1 class="mt-1 text-2xl font-bold text-navy">Không tìm thấy trang</h1>
      <p class="mt-2 text-sm leading-6 text-muted">Đường dẫn có thể đã thay đổi hoặc không tồn tại.</p>
      <RouterLink :to="{ name: 'home' }" class="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90">
        <ArrowLeft :size="16" aria-hidden="true" /> Về trang chủ
      </RouterLink>
    </section>
  </main>
</template>
