<script setup>
import { computed } from 'vue'
import { GraduationCap } from 'lucide-vue-next'
import { authState } from '@/service/authState'
import { getRoleLandingRouteName } from '@/service/authService'

const isAuthenticated = computed(() => Boolean(authState.accessToken && authState.user))
const dashboardRouteName = computed(() => getRoleLandingRouteName())
</script>

<template>
  <footer class="mt-auto border-t border-border bg-subtle/60">
    <div class="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-6 md:grid-cols-2 lg:grid-cols-4 lg:px-8">
      <div class="md:col-span-2">
        <RouterLink :to="{ name: 'home' }" class="inline-flex items-center gap-2" aria-label="EduSuggest trang chủ">
          <span class="flex size-7 items-center justify-center rounded-md bg-navy text-white">
            <GraduationCap :size="15" aria-hidden="true" />
          </span>
          <span class="text-base font-bold text-navy">Edu<span class="text-teal">Suggest</span></span>
        </RouterLink>
        <p class="mt-1.5 max-w-md text-xs leading-5 text-muted">
          Nền tảng khám phá gợi ý khóa học và tài liệu học tập.
        </p>
      </div>

      <div>
        <h2 class="text-xs font-bold text-navy">Khám phá</h2>
        <ul class="mt-1.5 space-y-1 text-xs text-muted">
          <li><RouterLink :to="{ name: 'home' }" class="transition-colors hover:text-teal">Trang chủ</RouterLink></li>
          <li><RouterLink :to="{ name: 'course-catalog' }" class="transition-colors hover:text-teal">Khóa học</RouterLink></li>
          <li><RouterLink :to="{ name: 'material-catalog' }" class="transition-colors hover:text-teal">Tài liệu học tập</RouterLink></li>
        </ul>
      </div>

      <div>
        <h2 class="text-xs font-bold text-navy">Tài khoản</h2>
        <ul class="mt-1.5 space-y-1 text-xs text-muted">
          <template v-if="!isAuthenticated">
            <li><RouterLink :to="{ name: 'login' }" class="transition-colors hover:text-teal">Đăng nhập</RouterLink></li>
            <li><RouterLink :to="{ name: 'register' }" class="transition-colors hover:text-teal">Đăng ký tài khoản</RouterLink></li>
          </template>
          <template v-else>
            <li><RouterLink :to="{ name: dashboardRouteName }" class="transition-colors hover:text-teal">Dashboard của tôi</RouterLink></li>
            <li><RouterLink :to="{ name: 'learning-progress' }" class="transition-colors hover:text-teal">Tiến độ học tập</RouterLink></li>
            <li><RouterLink :to="{ name: 'user-profile' }" class="transition-colors hover:text-teal">Hồ sơ cá nhân</RouterLink></li>
          </template>
        </ul>
      </div>
    </div>

    <div class="border-t border-border/70 px-4 py-2.5 text-center text-[11px] text-muted">
      © {{ new Date().getFullYear() }} EduSuggest · Nền tảng gợi ý khóa học và tài liệu học tập
    </div>
  </footer>
</template>
