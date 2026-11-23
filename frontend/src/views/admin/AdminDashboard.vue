<script setup>
import { ArrowUpRight, ClipboardList, FolderKanban, Users } from 'lucide-vue-next'

const sections = [
  { title: 'Hồ sơ nhà cung cấp', description: 'Xem và xử lý các hồ sơ đang chờ xét duyệt.', route: 'admin-provider-applications', icon: ClipboardList },
  { title: 'Tài khoản', description: 'Danh sách tài khoản và vai trò hiện có.', route: 'admin-users', icon: Users },
  { title: 'Danh mục', description: 'Quản lý các danh mục nội dung.', route: 'admin-categories', icon: FolderKanban },
]
</script>

<template>
  <main class="space-y-8">
    <header class="max-w-2xl border-b border-border pb-6">
      <p class="ui-eyebrow">Điều hành EduSuggest</p>
      <h1 class="ui-page-title mt-2">Không gian quản trị</h1>
      
    </header>
    <nav aria-label="Khu vực quản trị" class="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink v-for="section in sections" :key="section.route" :to="{ name: section.route }" class="group flex items-start gap-4 border-b border-border py-5 focus-visible:outline-2 focus-visible:outline-primary">
        <component :is="section.icon" :size="20" class="mt-1 shrink-0 text-secondary" aria-hidden="true" />
        <span class="min-w-0 flex-1"><span class="flex items-center gap-2 font-medium text-navy">{{ section.title }} <ArrowUpRight :size="15" class="opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" /></span><span class="mt-1 block text-sm leading-5 text-muted">{{ section.description }}</span></span>
      </RouterLink>
    </nav>
  </main>
</template>
