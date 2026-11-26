<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import {
  BarChart3,
  Bell,
  BookOpen,
  CalendarOff,
  ClipboardCheck,
  ClipboardList,
  Eye,
  FileText,
  GraduationCap,
  Layers,
  LayoutGrid,
  PanelLeftClose,
  PanelLeftOpen,
  Settings2,
  ShieldAlert,
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

function handleKeydown(event) {
  if (event.key === 'Escape') {
    emit('close-mobile')
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

const menuGroups = [
  {
    label: 'Tổng quan',
    links: [
      { label: 'Tổng quan', routeName: 'admin-dashboard', icon: LayoutGrid },
      { label: 'Thống kê hệ thống', routeName: 'admin-analytics', icon: BarChart3 },
      { label: 'Thương mại & Doanh thu', routeName: 'admin-commerce', icon: ClipboardCheck },
    ],
  },
  {
    label: 'Người dùng',
    links: [
      { label: 'Tài khoản', routeName: 'admin-users', icon: Users },
      { label: 'Chuyên gia', routeName: 'admin-reviewers', icon: UserCog },
      { label: 'Nhà cung cấp', routeName: 'admin-providers', icon: GraduationCap },
      { label: 'Hồ sơ đăng ký', routeName: 'admin-provider-applications', icon: ClipboardList },
    ],
  },
  {
    label: 'Điều hành chuyên gia',
    links: [
      { label: 'Tổng quan chuyên gia', routeName: 'admin-expert-overview', icon: UserCog },
      { label: 'Phân công kiểm duyệt', routeName: 'admin-assign-reviewer', icon: UserRound },
      { label: 'Hàng đợi phân công', routeName: 'admin-review-monitor', icon: ClipboardCheck },
      { label: 'Vi phạm & Kỷ luật', routeName: 'admin-accountability', icon: ShieldAlert },
      { label: 'Yêu cầu tạm ngừng', routeName: 'admin-availability', icon: CalendarOff },
    ],
  },
  {
    label: 'Nội dung & Hiển thị',
    links: [
      { label: 'Danh mục', routeName: 'admin-categories', icon: Tags },
      { label: 'Chuyên môn', routeName: 'admin-specialties', icon: Layers },
      { label: 'Khóa học', routeName: 'admin-courses', icon: BookOpen },
      { label: 'Tài liệu', routeName: 'admin-materials', icon: FileText },
      { label: 'Trạng thái hiển thị', routeName: 'admin-visibility', icon: Eye },
    ],
  },
  {
    label: 'Hệ thống',
    links: [
      { label: 'Cấu hình phân công', routeName: 'admin-assignment-config', icon: Settings2 },
      { label: 'Thông báo', routeName: 'admin-notifications', icon: Bell },
      { label: 'Hệ thống gợi ý', routeName: 'admin-recommendations', icon: Sparkles },
      { label: 'Hồ sơ cá nhân', routeName: 'admin-profile', icon: UserRound },
    ],
  },
]

function isActive(link) {
  return (
    route.name === link.routeName ||
    (route.name === 'admin-course-detail' && link.routeName === 'admin-courses') ||
    (route.name === 'admin-lesson-detail' && link.routeName === 'admin-courses') ||
    (route.name === 'admin-material-detail' && link.routeName === 'admin-materials')
  )
}
</script>

<template>
  <!-- Desktop Light Editorial Sidebar (unified with Provider & Reviewer) -->
  <aside
    class="sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 ease-out lg:flex"
    :class="collapsed ? 'w-[72px]' : 'w-[248px]'"
  >
    <!-- Brand + Collapse -->
    <div
      class="flex h-15 items-center border-b border-border/70 px-3.5"
      :class="collapsed ? 'justify-center' : 'justify-between gap-2'"
    >
      <RouterLink
        :to="{ name: 'admin-dashboard' }"
        class="flex min-w-0 items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        aria-label="EduSuggest Quản trị"
      >
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-navy text-white">
          <GraduationCap :size="17" aria-hidden="true" />
        </span>
        <span v-if="!collapsed" class="truncate text-[15px] font-bold tracking-tight text-navy">
          EduSuggest
        </span>
      </RouterLink>

      <button
        v-if="!collapsed"
        type="button"
        class="flex size-7 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors duration-150 hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        aria-label="Thu gọn thanh điều hướng"
        @click="emit('toggle-collapse')"
      >
        <PanelLeftClose :size="16" aria-hidden="true" />
      </button>
    </div>

    <!-- Navigation Groups -->
    <nav class="mt-4 flex-1 space-y-5 overflow-y-auto px-3 pb-4" aria-label="Điều hướng Quản trị">
      <section v-for="group in menuGroups" :key="group.label">
        <p
          v-if="!collapsed"
          class="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400"
        >
          {{ group.label }}
        </p>
        <div class="space-y-0.5">
          <RouterLink
            v-for="link in group.links"
            :key="link.routeName"
            :to="{ name: link.routeName }"
            class="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            :class="[
              collapsed ? 'justify-center' : '',
              isActive(link)
                ? 'bg-subtle font-semibold text-navy'
                : 'font-medium text-slate-600 hover:bg-subtle/70 hover:text-navy',
            ]"
            :title="collapsed ? link.label : undefined"
            :aria-current="isActive(link) ? 'page' : undefined"
          >
            <component
              :is="link.icon"
              :size="17"
              class="shrink-0 transition-colors duration-150"
              :class="isActive(link) ? 'text-teal' : 'text-slate-400 group-hover:text-navy'"
              aria-hidden="true"
            />
            <span v-if="!collapsed" class="min-w-0 flex-1 truncate">{{ link.label }}</span>
          </RouterLink>
        </div>
      </section>
    </nav>

    <!-- Bottom Expand Toggle (when collapsed) -->
    <div v-if="collapsed" class="border-t border-border/70 p-3">
      <button
        type="button"
        class="flex w-full items-center justify-center rounded-lg py-2 text-slate-400 transition-colors duration-150 hover:bg-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        aria-label="Mở rộng thanh điều hướng"
        @click="emit('toggle-collapse')"
      >
        <PanelLeftOpen :size="16" aria-hidden="true" />
      </button>
    </div>
  </aside>

  <!-- Mobile Drawer -->
  <Transition name="es-fade">
    <div v-if="mobileOpen" class="fixed inset-0 z-50 lg:hidden">
      <button
        type="button"
        class="absolute inset-0 bg-navy/40 backdrop-blur-[2px]"
        aria-label="Đóng menu"
        @click="emit('close-mobile')"
      ></button>

      <aside class="relative flex h-full w-[min(84vw,280px)] flex-col bg-surface shadow-2xl">
        <div class="flex h-15 items-center justify-between border-b border-border/70 px-4">
          <RouterLink
            :to="{ name: 'admin-dashboard' }"
            class="flex items-center gap-2.5"
            @click="emit('close-mobile')"
          >
            <span class="flex size-8 items-center justify-center rounded-lg bg-navy text-white">
              <GraduationCap :size="17" aria-hidden="true" />
            </span>
            <span class="text-[15px] font-bold tracking-tight text-navy">EduSuggest</span>
          </RouterLink>
          <button
            type="button"
            class="flex size-8 items-center justify-center rounded-lg text-slate-500 hover:bg-subtle hover:text-navy"
            aria-label="Đóng menu"
            @click="emit('close-mobile')"
          >
            <X :size="18" aria-hidden="true" />
          </button>
        </div>

        <nav class="mt-4 flex-1 space-y-5 overflow-y-auto px-3.5 pb-4" aria-label="Điều hướng Quản trị di động">
          <section v-for="group in menuGroups" :key="`mobile-${group.label}`">
            <p class="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
              {{ group.label }}
            </p>
            <div class="space-y-0.5">
              <RouterLink
                v-for="link in group.links"
                :key="`mobile-${link.routeName}`"
                :to="{ name: link.routeName }"
                class="flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-sm"
                :class="isActive(link) ? 'bg-subtle font-semibold text-navy' : 'font-medium text-slate-600 hover:bg-subtle/70 hover:text-navy'"
                @click="emit('close-mobile')"
              >
                <component :is="link.icon" :size="17" :class="isActive(link) ? 'text-teal' : 'text-slate-400'" aria-hidden="true" />
                <span class="flex-1 truncate">{{ link.label }}</span>
              </RouterLink>
            </div>
          </section>
        </nav>
      </aside>
    </div>
  </Transition>
</template>
