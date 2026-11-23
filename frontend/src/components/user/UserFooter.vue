<script setup>
import { GraduationCap } from 'lucide-vue-next'
</script>

<template>
  <footer class="mt-auto border-t border-slate-200 bg-white">
    <div class="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 md:grid-cols-2 lg:grid-cols-4 lg:px-8">
      <div class="md:col-span-2">
        <RouterLink :to="{ name: 'home' }" class="inline-flex items-center gap-2.5" aria-label="EduSuggest trang chủ">
          <span class="flex size-9 items-center justify-center rounded-xl bg-primary text-white"><GraduationCap :size="19" aria-hidden="true" /></span>
          <span class="text-lg font-bold text-navy">Edu<span class="text-primary">Suggest</span></span>
        </RouterLink>
        <p class="mt-3 max-w-md text-sm leading-6 text-muted">Khám phá khóa học và tài liệu học tập.</p>
      </div>
      <div>
        <h2 class="text-sm font-bold text-navy">Khám phá</h2>
        <ul class="mt-3 space-y-2 text-sm text-muted">
          <li><RouterLink :to="{ name: 'home' }" class="hover:text-primary">Trang chủ</RouterLink></li>
          <li><RouterLink :to="{ name: 'course-catalog' }" class="hover:text-primary">Danh sách khóa học</RouterLink></li>
          <li><RouterLink :to="{ name: 'material-catalog' }" class="hover:text-primary">Tài liệu học tập</RouterLink></li>
        </ul>
      </div>
      <div>
        <h2 class="text-sm font-bold text-navy">Hỗ trợ</h2>
        <ul class="mt-3 space-y-2 text-sm text-muted">
          <li><RouterLink :to="{ name: 'user-profile' }" class="hover:text-primary">Hồ sơ cá nhân</RouterLink></li>
          <li><RouterLink :to="{ name: 'learning-progress' }" class="hover:text-primary">Tiến độ học tập</RouterLink></li>
        </ul>
      </div>
    </div>
    <div class="border-t border-slate-100 px-4 py-4 text-center text-xs text-muted">© {{ new Date().getFullYear() }} EduSuggest</div>
  </footer>
</template>
