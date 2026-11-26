<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  BookOpen,
  ClipboardCheck,
  FileText,
  GraduationCap,
  History,
  LayoutGrid,
  PanelLeftClose,
  PanelLeftOpen,
  UserRound,
  X,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { loadProviderCourses, PROVIDER_STATUS } from '@/service/providerApiService'

defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-collapse', 'close-mobile'])
const route = useRoute()
const pendingCount = ref(0)

function handleKeydown(event) {
  if (event.key === 'Escape') {
    emit('close-mobile')
  }
}

onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  try {
    const courses = await loadProviderCourses()
    pendingCount.value = courses.filter((course) => course.status === PROVIDER_STATUS.pending).length
  } catch {
    pendingCount.value = 0
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

const navGroups = [
  {
    label: 'Biên soạn',
    items: [
      { label: 'Tổng quan', routeName: 'provider-dashboard', icon: LayoutGrid },
      { label: 'Khóa học', routeName: 'provider-courses', icon: BookOpen },
      { label: 'Tài liệu học tập', routeName: 'provider-materials-manage', icon: FileText },
      { label: 'Doanh thu & Bán hàng', routeName: 'provider-sales', icon: ClipboardCheck },
    ],
  },
  {
    label: 'Kiểm duyệt & Hồ sơ',
    items: [
      { label: 'Theo dõi duyệt', routeName: 'provider-reviews', icon: ClipboardCheck, showPending: true },
      { label: 'Lịch sử duyệt', routeName: 'provider-review-history', icon: History },
      { label: 'Hồ sơ', routeName: 'provider-profile', icon: UserRound },
    ],
  },
]

function isActive(item) {
  if (item.routeName === 'provider-courses') {
    return ['provider-courses', 'provider-course-detail', 'provider-course-edit'].includes(route.name)
  }
  return route.name === item.routeName
}
</script>

<template>
  <!-- Desktop Light Editorial Studio Sidebar -->
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
        :to="{ name: 'provider-dashboard' }"
        class="flex min-w-0 items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
        aria-label="EduSuggest"
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
    <nav class="mt-4 flex-1 space-y-6 overflow-y-auto px-3 pb-4" aria-label="Điều hướng Nhà cung cấp">
      <section v-for="group in navGroups" :key="group.label">
        <p
          v-if="!collapsed"
          class="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400"
        >
          {{ group.label }}
        </p>
        <div class="space-y-0.5">
          <RouterLink
            v-for="item in group.items"
            :key="item.routeName"
            :to="{ name: item.routeName }"
            class="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal"
            :class="[
              collapsed ? 'justify-center' : '',
              isActive(item)
                ? 'bg-subtle font-semibold text-navy'
                : 'font-medium text-slate-600 hover:bg-subtle/70 hover:text-navy',
            ]"
            :title="collapsed ? item.label : undefined"
            :aria-current="isActive(item) ? 'page' : undefined"
          >
            <component
              :is="item.icon"
              :size="17"
              class="shrink-0 transition-colors duration-150"
              :class="isActive(item) ? 'text-teal' : 'text-slate-400 group-hover:text-navy'"
              aria-hidden="true"
            />
            <span v-if="!collapsed" class="min-w-0 flex-1 truncate">{{ item.label }}</span>
            <span
              v-if="!collapsed && item.showPending && pendingCount"
              class="rounded-full bg-amber/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber tabular-nums"
            >
              {{ pendingCount }}
            </span>
          </RouterLink>
        </div>
      </section>
    </nav>

    <!-- Bottom Collapse Toggle (when collapsed) -->
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
            :to="{ name: 'provider-dashboard' }"
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

        <nav class="mt-4 flex-1 space-y-5 overflow-y-auto px-3.5 pb-4" aria-label="Điều hướng Provider di động">
          <section v-for="group in navGroups" :key="`mobile-${group.label}`">
            <p class="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
              {{ group.label }}
            </p>
            <div class="space-y-0.5">
              <RouterLink
                v-for="item in group.items"
                :key="`mobile-${item.routeName}`"
                :to="{ name: item.routeName }"
                class="flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-sm"
                :class="isActive(item) ? 'bg-subtle font-semibold text-navy' : 'font-medium text-slate-600 hover:bg-subtle/70 hover:text-navy'"
                @click="emit('close-mobile')"
              >
                <component :is="item.icon" :size="17" :class="isActive(item) ? 'text-teal' : 'text-slate-400'" aria-hidden="true" />
                <span class="flex-1 truncate">{{ item.label }}</span>
                <span
                  v-if="item.showPending && pendingCount"
                  class="rounded-full bg-amber/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber"
                >
                  {{ pendingCount }}
                </span>
              </RouterLink>
            </div>
          </section>
        </nav>
      </aside>
    </div>
  </Transition>
</template>
