<script setup>
import {
  BarChart3,
  BookOpen,
  BookOpenText,
  ClipboardList,
  Eye,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Sparkles,
  Tags,
  UserCog,
  UserRound,
  Users,
  X,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'

defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-collapse', 'close-mobile'])
const route = useRoute()

const menuGroups = [
  {
    label: 'Tổng quan',
    links: [{ label: 'Dashboard', routeName: 'admin-dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Quản lý người dùng',
    links: [
      { label: 'Tài khoản', routeName: 'admin-users', icon: Users },
      { label: 'Chuyên gia', routeName: 'admin-reviewers', icon: UserCog },
      { label: 'Người cung cấp', routeName: 'admin-providers', icon: GraduationCap },
      { label: 'Hồ sơ đăng ký', routeName: 'admin-provider-applications', icon: ClipboardList },
    ],
  },
  {
    label: 'Quản lý nội dung',
    links: [
      { label: 'Danh mục', routeName: 'admin-categories', icon: Tags },
      { label: 'Khóa học', routeName: 'admin-courses', icon: BookOpen },
      { label: 'Tài liệu', routeName: 'admin-materials', icon: FileText },
      { label: 'Trạng thái hiển thị', routeName: 'admin-visibility', icon: Eye },
    ],
  },
  {
    label: 'Kiểm duyệt',
    links: [
      { label: 'Phân công Reviewer', routeName: 'admin-assign-reviewer', icon: UserRound },
      { label: 'Theo dõi kiểm duyệt', routeName: 'admin-review-monitor', icon: ClipboardList },
    ],
  },
  {
    label: 'Hệ thống',
    links: [
      { label: 'Hệ thống gợi ý', routeName: 'admin-recommendations', icon: Sparkles },
      { label: 'Thống kê hệ thống', routeName: 'admin-analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'Tài khoản',
    links: [{ label: 'Thông tin cá nhân', routeName: 'admin-profile', icon: UserRound }],
  },
]

function isActive(link) {
  return route.name === link.routeName
    || (route.name === 'admin-course-detail' && link.routeName === 'admin-courses')
    || (route.name === 'admin-lesson-detail' && link.routeName === 'admin-courses')
    || (route.name === 'admin-material-detail' && link.routeName === 'admin-materials')
}
</script>

<template>
  <aside class="sticky top-0 hidden h-screen shrink-0 flex-col overflow-y-auto bg-navy px-3 py-5 text-white transition-[width] duration-200 lg:flex" :class="collapsed ? 'w-20' : 'w-[270px]'">
    <div class="flex items-center justify-between gap-2 px-1">
      <RouterLink :to="{ name: 'admin-dashboard' }" class="flex min-w-0 items-center gap-2.5" aria-label="EduSuggest Admin">
        <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-accent text-navy">
          <GraduationCap :size="21" aria-hidden="true" />
        </span>
        <span v-if="!collapsed" class="min-w-0">
          <span class="block truncate text-base font-bold">EduSuggest</span>
          <span class="block text-[10px] font-semibold tracking-[0.18em] text-white/55">ADMIN</span>
        </span>
      </RouterLink>
      <button
        v-if="!collapsed"
        type="button"
        class="flex size-8 shrink-0 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white"
        aria-label="Thu gọn thanh điều hướng"
        @click="emit('toggle-collapse')"
      >
        <BookOpenText :size="17" aria-hidden="true" />
      </button>
    </div>
    <button v-if="collapsed" type="button" class="mx-auto mt-3 flex size-9 items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white" aria-label="Mở rộng thanh điều hướng" @click="emit('toggle-collapse')">
      <BookOpenText :size="17" aria-hidden="true" />
    </button>

    <nav class="mt-7 flex-1 space-y-5" aria-label="Điều hướng quản trị">
      <section v-for="group in menuGroups" :key="group.label">
        <p v-if="!collapsed" class="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/45">{{ group.label }}</p>
        <div class="space-y-1">
          <RouterLink
            v-for="link in group.links"
            :key="link.routeName"
            :to="{ name: link.routeName }"
            class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            :class="isActive(link) ? 'bg-white/10 font-semibold text-white ring-1 ring-inset ring-white/15' : 'text-white/70 hover:bg-white/10 hover:text-white'"
            :title="collapsed ? link.label : undefined"
            :aria-current="isActive(link) ? 'page' : undefined"
            @click="emit('close-mobile')"
          >
            <component :is="link.icon" class="shrink-0" :size="18" aria-hidden="true" />
            <span v-if="!collapsed" class="truncate">{{ link.label }}</span>
          </RouterLink>
        </div>
      </section>
    </nav>


  </aside>

  <div v-if="mobileOpen" class="fixed inset-0 z-50 lg:hidden">
    <button type="button" class="absolute inset-0 bg-navy/55" aria-label="Đóng menu" @click="emit('close-mobile')"></button>
    <aside class="relative flex h-full w-[min(86vw,300px)] flex-col overflow-y-auto bg-navy px-3 py-5 text-white shadow-xl">
      <div class="flex items-center justify-between gap-3 px-1">
        <RouterLink :to="{ name: 'admin-dashboard' }" class="flex items-center gap-2.5" @click="emit('close-mobile')">
          <span class="flex size-10 items-center justify-center rounded-xl bg-brand-accent text-navy">
            <GraduationCap :size="21" aria-hidden="true" />
          </span>
          <span>
            <span class="block text-base font-bold">EduSuggest</span>
            <span class="block text-[10px] font-semibold tracking-[0.18em] text-white/55">ADMIN</span>
          </span>
        </RouterLink>
        <button type="button" class="flex size-9 items-center justify-center rounded-lg text-white/70 hover:bg-white/10" aria-label="Đóng menu" @click="emit('close-mobile')">
          <X :size="19" aria-hidden="true" />
        </button>
      </div>
      <nav class="mt-7 flex-1 space-y-5" aria-label="Điều hướng quản trị di động">
        <section v-for="group in menuGroups" :key="group.label">
          <p class="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/45">{{ group.label }}</p>
          <div class="space-y-1">
            <RouterLink
              v-for="link in group.links"
              :key="link.routeName"
              :to="{ name: link.routeName }"
              class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm"
              :class="isActive(link) ? 'bg-white/10 font-semibold text-white ring-1 ring-inset ring-white/15' : 'text-white/70 hover:bg-white/10 hover:text-white'"
              @click="emit('close-mobile')"
            >
              <component :is="link.icon" class="shrink-0" :size="18" aria-hidden="true" />
              {{ link.label }}
            </RouterLink>
          </div>
        </section>
      </nav>
    </aside>
  </div>
</template>
