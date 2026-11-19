<script setup>
import { computed } from 'vue'
import { KeyRound } from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()
const isRegister = computed(() => route.name === 'provider-register')
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-background p-4">
    <section class="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-8">
      <span class="mx-auto flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary"><KeyRound :size="22" aria-hidden="true" /></span>
      <p class="mt-4 text-sm font-semibold text-primary">EduSuggest · Course Provider</p>
      <h1 class="mt-2 text-2xl font-bold text-navy">{{ isRegister ? 'Đăng ký tài khoản' : 'Đăng nhập Provider' }}</h1>
      <div class="mt-5 rounded-xl border border-slate-200 bg-background p-4 text-left text-sm leading-6 text-muted">
        {{ isRegister
          ? 'Chức năng đăng ký tài khoản chưa được kết nối API. Khi tích hợp, lựa chọn vai trò Provider sẽ nằm trong quy trình đăng ký; không cần gửi yêu cầu riêng.'
          : 'Chức năng đăng nhập và phân quyền chưa được kết nối. Trang này không thu thập mật khẩu và không giả lập đăng nhập thành công.' }}
      </div>
      <p class="mt-4 text-xs leading-5 text-muted">Khu vực quản lý Provider hiện là bản xem trước dùng dữ liệu mock; chưa có xác thực hoặc cách ly dữ liệu theo tài khoản.</p>
      <div class="mt-5 flex flex-wrap justify-center gap-2">
        <RouterLink :to="{ name: 'home' }" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background">Về trang chủ</RouterLink>
        <RouterLink :to="{ name: 'provider-dashboard' }" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90">Xem bản demo Provider</RouterLink>
      </div>
    </section>
  </main>
</template>
