<script setup>
import {
  BookOpenCheck,
  ClipboardList,
  FileCheck2,
  LayoutDashboard,
  UserRound,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()
const overviewLink = { label: 'Tổng quan', routeName: 'reviewer-dashboard', icon: LayoutDashboard }
const reviewLinks = [
  { label: 'Khóa học chờ duyệt', routeName: 'reviewer-courses', icon: BookOpenCheck },
  { label: 'Tài liệu chờ duyệt', routeName: 'reviewer-materials', icon: FileCheck2 },
  { label: 'Lịch sử kiểm duyệt', routeName: 'reviewer-history', icon: ClipboardList },
]

const personalLinks = [
  { label: 'Hồ sơ cá nhân', routeName: 'reviewer-profile', icon: UserRound },
]

function isActive(routeName) {
  return (
    route.name === routeName ||
    (route.name === 'reviewer-course-detail' && routeName === 'reviewer-courses') ||
    (route.name === 'reviewer-material-detail' && routeName === 'reviewer-materials')
  )
}
</script>

<template>
  <aside class="hidden min-h-screen flex-col bg-navy px-4 py-6 text-white lg:flex">
    <RouterLink :to="{ name: 'reviewer-dashboard' }" class="flex items-center gap-3 px-2">
      <span class="flex size-10 items-center justify-center rounded-xl bg-brand-accent text-navy">
        <BookOpenCheck :size="21" aria-hidden="true" />
      </span>
      <span class="text-lg font-bold tracking-tight">EduSuggest</span>
    </RouterLink>

    <p class="mb-2 mt-9 px-3 text-xs font-semibold uppercase tracking-wider text-white/50">Tổng quan</p>
    <nav class="space-y-1" aria-label="Tổng quan kiểm duyệt">
      <RouterLink
        :to="{ name: overviewLink.routeName }"
        class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        :class="isActive(overviewLink.routeName) ? 'bg-white/10 font-semibold text-white ring-1 ring-inset ring-white/15' : 'text-white/75 hover:bg-white/10 hover:text-white'"
      >
        <component :is="overviewLink.icon" :size="18" aria-hidden="true" />
        {{ overviewLink.label }}
      </RouterLink>
    </nav>

    <p class="mb-2 mt-8 px-3 text-xs font-semibold uppercase tracking-wider text-white/50">Quản lý kiểm duyệt</p>
    <nav class="space-y-1" aria-label="Quản lý kiểm duyệt">
      <RouterLink
        v-for="link in reviewLinks"
        :key="link.routeName"
        :to="{ name: link.routeName }"
        class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        :class="isActive(link.routeName) ? 'bg-white/10 font-semibold text-white ring-1 ring-inset ring-white/15' : 'text-white/75 hover:bg-white/10 hover:text-white'"
      >
        <component :is="link.icon" :size="18" aria-hidden="true" />
        {{ link.label }}
      </RouterLink>
    </nav>

    <p class="mb-2 mt-8 px-3 text-xs font-semibold uppercase tracking-wider text-white/50">Cá nhân</p>
    <nav class="space-y-1" aria-label="Tài khoản kiểm duyệt">
      <RouterLink
        v-for="link in personalLinks"
        :key="link.routeName"
        :to="{ name: link.routeName }"
        class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        :class="isActive(link.routeName) ? 'bg-white/10 font-semibold text-white ring-1 ring-inset ring-white/15' : 'text-white/75 hover:bg-white/10 hover:text-white'"
      >
        <component :is="link.icon" :size="18" aria-hidden="true" />
        {{ link.label }}
      </RouterLink>
    </nav>

    <div class="mt-auto rounded-xl border border-white/10 bg-white/5 p-4">
      <p class="text-sm font-semibold">Không gian kiểm duyệt</p>
      <p class="mt-1 text-xs leading-5 text-white/60">Khóa học được tải từ dịch vụ kiểm duyệt.</p>
    </div>
  </aside>

  <nav class="flex gap-2 overflow-x-auto border-b border-slate-200 bg-white px-4 py-3 lg:hidden" aria-label="Điều hướng kiểm duyệt trên di động">
    <RouterLink
      :to="{ name: overviewLink.routeName }"
      class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition"
      :class="isActive(overviewLink.routeName) ? 'bg-primary text-white' : 'text-muted hover:bg-background hover:text-navy'"
    >
      <component :is="overviewLink.icon" :size="16" aria-hidden="true" />
      {{ overviewLink.label }}
    </RouterLink>
    <RouterLink
      v-for="link in reviewLinks"
      :key="link.routeName"
      :to="{ name: link.routeName }"
      class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition"
      :class="isActive(link.routeName) ? 'bg-primary text-white' : 'text-muted hover:bg-background hover:text-navy'"
    >
      <component :is="link.icon" :size="16" aria-hidden="true" />
      {{ link.label }}
    </RouterLink>
    <RouterLink
      :to="{ name: 'reviewer-profile' }"
      class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted hover:bg-background hover:text-navy"
    >
      <UserRound :size="16" aria-hidden="true" />
      Hồ sơ
    </RouterLink>
  </nav>
</template>
