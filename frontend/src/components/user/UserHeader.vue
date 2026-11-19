<script setup>
import { computed, ref } from 'vue'
import {
  Bell,
  BookOpen,
  ChevronDown,
  GraduationCap,
  History,
  LayoutDashboard,
  LogIn,
  Menu,
  Search,
  Sparkles,
  UserRound,
  UserPlus,
  X,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { getRecentLearningActivities, getUserProfile, hasProviderRole } from '@/service/userService'

const route = useRoute()
const router = useRouter()
const profile = getUserProfile()
const searchQuery = ref(typeof route.query.q === 'string' ? route.query.q : '')
const mobileOpen = ref(false)
const accountOpen = ref(false)
const notificationsOpen = ref(false)
const feedback = ref('')
const notifications = computed(() => getRecentLearningActivities(4))
const initials = computed(() => profile.fullName.split(/\s+/).slice(-2).map((part) => part[0]).join('').toLocaleUpperCase('vi'))

async function submitSearch() {
  const query = searchQuery.value.trim()
  await router.push({ name: 'course-catalog', query: query ? { q: query } : {} })
  mobileOpen.value = false
}

function endDemoSession() {
  accountOpen.value = false
  feedback.value = 'Chưa có phiên đăng nhập thật để kết thúc. API xác thực chưa được tích hợp.'
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
    <div class="mx-auto flex min-h-[72px] max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
      <div class="flex min-w-0 items-center gap-3">
        <button type="button" class="flex size-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-navy hover:bg-background md:hidden" aria-label="Mở menu" :aria-expanded="mobileOpen" @click="mobileOpen = !mobileOpen">
          <Menu v-if="!mobileOpen" :size="19" aria-hidden="true" /><X v-else :size="19" aria-hidden="true" />
        </button>
        <RouterLink :to="{ name: 'home' }" class="flex shrink-0 items-center gap-2.5" aria-label="EduSuggest trang chủ">
          <span class="flex size-10 items-center justify-center rounded-xl bg-primary text-white"><GraduationCap :size="22" aria-hidden="true" /></span>
          <span class="text-lg font-bold tracking-tight text-navy sm:text-xl">Edu<span class="text-primary">Suggest</span></span>
        </RouterLink>
      </div>

      <nav class="hidden items-center gap-4 lg:flex" aria-label="Điều hướng người học">
        <RouterLink :to="{ name: 'home' }" class="text-sm font-medium text-muted hover:text-primary">Trang chủ</RouterLink>
        <RouterLink :to="{ name: 'course-catalog' }" class="text-sm font-medium text-muted hover:text-primary">Khóa học</RouterLink>
        <RouterLink :to="{ name: 'material-catalog' }" class="text-sm font-medium text-muted hover:text-primary">Tài liệu</RouterLink>
        <RouterLink :to="{ name: 'learning-progress' }" class="text-sm font-medium text-muted hover:text-primary">Khóa học của tôi</RouterLink>
        <RouterLink :to="{ name: 'course-recommendations' }" class="inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-primary"><Sparkles :size="14" aria-hidden="true" /> Gợi ý</RouterLink>
      </nav>

      <div class="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <form class="hidden w-44 lg:block xl:w-56" role="search" @submit.prevent="submitSearch">
          <label class="relative block">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="16" aria-hidden="true" />
            <input v-model="searchQuery" type="search" placeholder="Tìm khóa học..." aria-label="Tìm khóa học" class="w-full rounded-xl border border-slate-200 bg-background py-2 pl-9 pr-3 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          </label>
        </form>

        <div class="relative">
          <button type="button" class="relative flex size-10 items-center justify-center rounded-xl text-muted hover:bg-background hover:text-navy" aria-label="Thông báo người học" :aria-expanded="notificationsOpen" @click="notificationsOpen = !notificationsOpen; accountOpen = false">
            <Bell :size="19" aria-hidden="true" />
            <span v-if="notifications.length" class="absolute right-2 top-2 size-2 rounded-full bg-accent" aria-label="Có hoạt động gần đây"></span>
          </button>
          <div v-if="notificationsOpen" class="absolute right-0 top-12 z-40 w-[min(88vw,340px)] rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
            <p class="font-semibold text-navy">Hoạt động gần đây</p>
            <ul v-if="notifications.length" class="mt-2 divide-y divide-slate-100">
              <li v-for="item in notifications" :key="item.id" class="py-2.5 text-sm text-muted">{{ item.title }}</li>
            </ul>
            <p v-else class="mt-2 text-sm text-muted">Chưa có hoạt động.</p>
          </div>
        </div>

        <div class="relative">
          <button type="button" class="flex items-center gap-2 rounded-xl p-1.5 hover:bg-background" aria-label="Mở menu tài khoản" :aria-expanded="accountOpen" @click="accountOpen = !accountOpen; notificationsOpen = false">
            <span v-if="profile.avatarUrl" class="size-9 overflow-hidden rounded-full"><img :src="profile.avatarUrl" alt="" class="h-full w-full object-cover"></span>
            <span v-else class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{{ initials }}</span>
            <span class="hidden max-w-28 truncate text-sm font-semibold text-navy xl:block">{{ profile.fullName }}</span>
            <ChevronDown class="hidden text-muted xl:block" :size="14" aria-hidden="true" />
          </button>
          <div v-if="accountOpen" class="absolute right-0 top-12 z-40 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
            <p class="px-3 py-2 text-xs text-muted">Hồ sơ minh họa · chưa đăng nhập thật</p>
            <RouterLink :to="{ name: 'user-profile' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><UserRound :size="15" aria-hidden="true" /> Hồ sơ cá nhân</RouterLink>
            <RouterLink :to="{ name: 'user-dashboard' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><LayoutDashboard :size="15" aria-hidden="true" /> Dashboard học tập</RouterLink>
            <RouterLink :to="{ name: 'learning-progress' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><LayoutDashboard :size="15" aria-hidden="true" /> Tiến độ học tập</RouterLink>
            <RouterLink :to="{ name: 'learning-history' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><History :size="15" aria-hidden="true" /> Lịch sử học tập</RouterLink>
            <RouterLink :to="{ name: 'expert-reviews' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><BookOpen :size="15" aria-hidden="true" /> Đánh giá chuyên gia</RouterLink>
            <RouterLink v-if="!hasProviderRole()" :to="{ name: 'provider-application' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><UserPlus :size="15" aria-hidden="true" /> Đăng ký Provider</RouterLink>
            <RouterLink v-else :to="{ name: 'provider-dashboard' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy hover:bg-background" @click="accountOpen = false"><GraduationCap :size="15" aria-hidden="true" /> Quản lý khóa học</RouterLink>
            <RouterLink :to="{ name: 'login' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-primary hover:bg-background" @click="accountOpen = false"><LogIn :size="15" aria-hidden="true" /> Đăng nhập</RouterLink>
            <RouterLink :to="{ name: 'register' }" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-primary hover:bg-background" @click="accountOpen = false"><UserPlus :size="15" aria-hidden="true" /> Đăng ký tài khoản</RouterLink>
            <button type="button" class="mt-1 w-full rounded-lg px-3 py-2 text-left text-sm text-muted hover:bg-background" @click="endDemoSession">Đăng xuất</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="mobileOpen" class="border-t border-slate-100 bg-white px-4 py-4 md:hidden">
      <form class="mb-3" role="search" @submit.prevent="submitSearch">
        <label class="relative block">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="16" aria-hidden="true" />
          <input v-model="searchQuery" type="search" placeholder="Tìm khóa học..." aria-label="Tìm khóa học" class="w-full rounded-xl border border-slate-200 bg-background py-2.5 pl-9 pr-3 text-sm text-navy outline-none focus:border-primary">
        </label>
      </form>
      <nav class="grid grid-cols-2 gap-2" aria-label="Menu người học di động">
        <RouterLink v-for="item in [
          { label: 'Trang chủ', name: 'home' },
          { label: 'Khóa học', name: 'course-catalog' },
          { label: 'Tài liệu', name: 'material-catalog' },
          { label: 'Khóa học của tôi', name: 'learning-progress' },
          { label: 'Gợi ý dành cho bạn', name: 'course-recommendations' },
          { label: 'Hồ sơ cá nhân', name: 'user-profile' },
        ]" :key="item.name" :to="{ name: item.name }" class="rounded-lg px-3 py-2 text-sm font-medium text-navy hover:bg-background" @click="mobileOpen = false">
          {{ item.label }}
        </RouterLink>
      </nav>
    </div>

    <div v-if="feedback" class="fixed bottom-4 right-4 z-50 max-w-sm rounded-xl border border-slate-200 bg-white p-4 text-sm text-navy shadow-lg" role="status">
      {{ feedback }}
      <button type="button" class="ml-3 font-semibold text-primary hover:underline" @click="feedback = ''">Đóng</button>
    </div>
  </header>
</template>
