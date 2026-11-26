<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  Bell,
  BookOpen,
  ChevronDown,
  GraduationCap,
  Heart,
  History,
  LayoutDashboard,
  Menu,
  ReceiptText,
  ShoppingCart,
  UserPlus,
  UserRound,
  X,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { fetchLearningHistory } from '@/service/userApiService'
import { authState } from '@/service/authState'
import {
  getRoleLandingRouteName,
  getRoleName,
  loadCurrentUser,
  logoutAccount,
} from '@/service/authService'
import {
  commerceState,
  dismissCommerceToast,
  loadCommerceCapabilities,
  resetCommerceState,
  syncLearnerCommerceState,
} from '@/service/commerceState'

const route = useRoute()
const router = useRouter()

const fullName = computed(() => authState.user?.hoTen || authState.user?.tenTaiKhoan || '')
const shortName = computed(() => {
  const parts = fullName.value.trim().split(/\s+/).filter(Boolean)
  if (parts.length <= 2) return parts.join(' ')
  return parts.slice(-2).join(' ')
})
const isAuthenticated = computed(() => Boolean(authState.accessToken && authState.user))
const roleName = computed(() => getRoleName())
const isLearner = computed(() => roleName.value === 'USER')
const isProvider = computed(() => roleName.value === 'PROVIDER')
const dashboardRouteName = computed(() => getRoleLandingRouteName())
const showMarketplaceActions = computed(
  () => isAuthenticated.value && isLearner.value && commerceState.marketplaceEnabled,
)

function isNavActive(section) {
  const name = String(route.name || '')
  if (section === 'home') return name === 'home'
  if (section === 'courses') return name === 'course-catalog' || name === 'course-detail'
  if (section === 'materials') return name === 'material-catalog' || name === 'material-detail'
  if (section === 'my-courses') {
    return (
      name === 'user-dashboard'
      || name === 'learning-progress'
      || name === 'learning-history'
      || name === 'learning'
    )
  }
  if (section === 'recommendations') return name.includes('recommendation')
  return false
}

const mobileOpen = ref(false)
const accountOpen = ref(false)
const notificationsOpen = ref(false)
const headerRef = ref(null)
const mobileToggleButtonRef = ref(null)
const notificationsContainerRef = ref(null)
const notificationsButtonRef = ref(null)
const accountContainerRef = ref(null)
const accountButtonRef = ref(null)
const feedback = ref('')
let feedbackTimer = null
const recentActivities = ref([])
const loadingActivities = ref(false)
const activitiesLoaded = ref(false)

const initials = computed(() =>
  fullName.value
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join('')
    .toLocaleUpperCase('vi') || 'ES',
)

function formatActivityTime(timestamp) {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

async function loadActivities() {
  if (!isAuthenticated.value || !isLearner.value) {
    recentActivities.value = []
    return
  }
  loadingActivities.value = true
  try {
    const history = await fetchLearningHistory()
    recentActivities.value = (history || []).slice(0, 5)
  } catch {
    recentActivities.value = []
  } finally {
    loadingActivities.value = false
    activitiesLoaded.value = true
  }
}

watch([isAuthenticated, isLearner], ([authed, learner]) => {
  if (authed && learner) {
    loadActivities()
  } else {
    recentActivities.value = []
    activitiesLoaded.value = false
  }
})

watch(() => route.fullPath, () => {
  notificationsOpen.value = false
  accountOpen.value = false
  mobileOpen.value = false
})

function handleDocumentPointerDown(event) {
  const target = event.target
  if (
    notificationsOpen.value
    && notificationsContainerRef.value
    && !notificationsContainerRef.value.contains(target)
  ) {
    notificationsOpen.value = false
  }
  if (
    accountOpen.value
    && accountContainerRef.value
    && !accountContainerRef.value.contains(target)
  ) {
    accountOpen.value = false
  }
  if (
    mobileOpen.value
    && headerRef.value
    && !headerRef.value.contains(target)
  ) {
    mobileOpen.value = false
  }
}

function handleDocumentKeydown(event) {
  if (event.key !== 'Escape') return
  if (notificationsOpen.value) {
    notificationsOpen.value = false
    notificationsButtonRef.value?.focus()
    return
  }
  if (accountOpen.value) {
    accountOpen.value = false
    accountButtonRef.value?.focus()
    return
  }
  if (mobileOpen.value) {
    mobileOpen.value = false
    mobileToggleButtonRef.value?.focus()
  }
}

onMounted(async () => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleDocumentKeydown)
  loadCommerceCapabilities()
  if (!authState.accessToken || authState.user) {
    if (isAuthenticated.value && isLearner.value) {
      loadActivities()
      syncLearnerCommerceState()
    }
    return
  }
  try {
    await loadCurrentUser()
    if (isAuthenticated.value && isLearner.value) {
      loadActivities()
      syncLearnerCommerceState()
    }
  } catch {
    // Keep public navigation intact if session is unavailable
  }
})

function dismissFeedback() {
  if (feedbackTimer) {
    clearTimeout(feedbackTimer)
    feedbackTimer = null
  }
  feedback.value = ''
}

function showFeedback(message) {
  if (feedbackTimer) {
    clearTimeout(feedbackTimer)
    feedbackTimer = null
  }
  feedback.value = message
  feedbackTimer = setTimeout(() => {
    feedback.value = ''
    feedbackTimer = null
  }, 3800)
}

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleDocumentKeydown)
  if (feedbackTimer) {
    clearTimeout(feedbackTimer)
    feedbackTimer = null
  }
})

function toggleNotifications() {
  notificationsOpen.value = !notificationsOpen.value
  accountOpen.value = false
  if (notificationsOpen.value && isAuthenticated.value && isLearner.value && !activitiesLoaded.value) {
    loadActivities()
  }
}

async function endSession() {
  accountOpen.value = false
  mobileOpen.value = false
  resetCommerceState()
  try {
    await logoutAccount()
    showFeedback('Bạn đã đăng xuất khỏi tài khoản.')
    await router.replace({ name: 'home' })
  } catch {
    showFeedback('Phiên đăng nhập trên trình duyệt đã được đóng.')
    await router.replace({ name: 'home' })
  }
}
</script>

<template>
  <header
    ref="headerRef"
    class="sticky top-0 z-30 border-b border-border/80 bg-surface/95 backdrop-blur-md"
  >
    <!-- Row 1: Main Navigation -->
    <div class="mx-auto flex h-[60px] max-w-7xl items-center justify-between gap-3 px-4 sm:h-16 sm:px-6 lg:px-8">
      <!-- Left: Mobile toggle + Brand -->
      <div class="flex shrink-0 items-center gap-2.5">
        <button
          ref="mobileToggleButtonRef"
          type="button"
          class="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border/90 text-navy transition-[background-color,border-color,transform] duration-150 hover:bg-subtle active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40 lg:hidden"
          aria-label="Mở menu điều hướng"
          :aria-expanded="mobileOpen"
          @click="mobileOpen = !mobileOpen"
        >
          <Menu v-if="!mobileOpen" :size="18" aria-hidden="true" />
          <X v-else :size="18" aria-hidden="true" />
        </button>

        <RouterLink
          :to="{ name: 'home' }"
          class="flex shrink-0 items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40 focus-visible:ring-offset-2"
          aria-label="EduSuggest trang chủ"
        >
          <span class="flex size-9 items-center justify-center rounded-lg bg-navy text-white">
            <GraduationCap :size="19" aria-hidden="true" />
          </span>
          <span class="text-lg font-bold tracking-[-0.02em] text-navy">
            Edu<span class="text-teal">Suggest</span>
          </span>
        </RouterLink>
      </div>

      <!-- Center: Primary Navigation Links -->
      <nav
        class="hidden min-w-0 flex-1 items-center justify-center gap-1 lg:flex xl:gap-2"
        aria-label="Điều hướng chính"
      >
        <RouterLink
          :to="{ name: 'home' }"
          :aria-current="isNavActive('home') ? 'page' : undefined"
          :class="[
            'relative whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40',
            isNavActive('home')
              ? 'font-semibold text-navy after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal'
              : 'font-medium text-muted hover:bg-subtle/70 hover:text-navy',
          ]"
        >
          Khám phá
        </RouterLink>
        <RouterLink
          :to="{ name: 'course-catalog' }"
          :aria-current="isNavActive('courses') ? 'page' : undefined"
          :class="[
            'relative whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40',
            isNavActive('courses')
              ? 'font-semibold text-navy after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal'
              : 'font-medium text-muted hover:bg-subtle/70 hover:text-navy',
          ]"
        >
          Khóa học
        </RouterLink>
        <RouterLink
          :to="{ name: 'material-catalog' }"
          :aria-current="isNavActive('materials') ? 'page' : undefined"
          :class="[
            'relative whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40',
            isNavActive('materials')
              ? 'font-semibold text-navy after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal'
              : 'font-medium text-muted hover:bg-subtle/70 hover:text-navy',
          ]"
        >
          Tài liệu học tập
        </RouterLink>
        <RouterLink
          v-if="isAuthenticated && isLearner"
          :to="{ name: 'user-dashboard' }"
          :aria-current="isNavActive('my-courses') ? 'page' : undefined"
          :class="[
            'relative whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40',
            isNavActive('my-courses')
              ? 'font-semibold text-navy after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal'
              : 'font-medium text-muted hover:bg-subtle/70 hover:text-navy',
          ]"
        >
          Học tập của tôi
        </RouterLink>
        <RouterLink
          v-if="isAuthenticated && isLearner"
          :to="{ name: 'course-recommendations' }"
          :aria-current="isNavActive('recommendations') ? 'page' : undefined"
          :class="[
            'relative whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40',
            isNavActive('recommendations')
              ? 'font-semibold text-navy after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-teal'
              : 'font-medium text-muted hover:bg-subtle/70 hover:text-navy',
          ]"
        >
          Gợi ý
        </RouterLink>
      </nav>

      <!-- Right: Auth CTAs (Guest) or Activity & Account Controls (Authenticated) -->
      <div class="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <template v-if="!isAuthenticated">
          <RouterLink
            :to="{ name: 'login' }"
            class="ui-button ui-button--outline ui-button--sm active:scale-[0.97]"
          >
            Đăng nhập
          </RouterLink>
          <RouterLink
            :to="{ name: 'register' }"
            class="ui-button ui-button--primary ui-button--sm hidden active:scale-[0.97] sm:inline-flex"
          >
            Đăng ký
          </RouterLink>
        </template>

        <template v-else>
          <RouterLink
            v-if="!isLearner"
            :to="{ name: dashboardRouteName }"
            class="ui-button ui-button--outline ui-button--sm hidden items-center gap-1.5 active:scale-[0.97] xl:inline-flex"
          >
            <LayoutDashboard :size="14" aria-hidden="true" />
            <span>Không gian quản lý</span>
          </RouterLink>

          <!-- Marketplace Icons: Wishlist & Shopping Cart (only when Marketplace is enabled) -->
          <template v-if="showMarketplaceActions">
            <RouterLink
              :to="{ name: 'wishlist' }"
              class="relative flex size-9 items-center justify-center rounded-lg text-muted transition-[background-color,color,transform] duration-150 hover:bg-subtle hover:text-navy active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
              :aria-label="`Danh sách yêu thích (${commerceState.wishlistCount} khóa học)`"
              title="Danh sách yêu thích"
            >
              <Heart :size="18" aria-hidden="true" />
              <span
                v-if="commerceState.wishlistCount > 0"
                class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-navy px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface tabular-nums"
              >
                {{ commerceState.wishlistCount > 99 ? '99+' : commerceState.wishlistCount }}
              </span>
            </RouterLink>

            <RouterLink
              :to="{ name: 'cart' }"
              class="relative flex size-9 items-center justify-center rounded-lg text-muted transition-[background-color,color,transform] duration-150 hover:bg-subtle hover:text-navy active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
              :aria-label="`Giỏ hàng (${commerceState.cartCount} khóa học)`"
              title="Giỏ hàng"
            >
              <ShoppingCart :size="18" aria-hidden="true" />
              <span
                v-if="commerceState.cartCount > 0"
                class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-teal px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface tabular-nums"
              >
                {{ commerceState.cartCount > 99 ? '99+' : commerceState.cartCount }}
              </span>
            </RouterLink>
          </template>

          <!-- Learner Activity Bell -->
          <div v-if="isLearner" ref="notificationsContainerRef" class="relative">
            <button
              ref="notificationsButtonRef"
              type="button"
              class="relative flex size-9 items-center justify-center rounded-lg text-muted transition-[background-color,color,transform] duration-150 hover:bg-subtle hover:text-navy active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
              aria-label="Hoạt động học tập gần đây"
              :aria-expanded="notificationsOpen"
              @click="toggleNotifications"
            >
              <Bell :size="18" aria-hidden="true" />
              <span
                v-if="recentActivities.length"
                class="absolute right-2 top-2 size-2 rounded-full bg-amber ring-2 ring-surface"
                aria-label="Có hoạt động gần đây"
              />
            </button>

            <Transition name="es-header-popover">
              <div
                v-if="notificationsOpen"
                class="absolute right-0 top-11 z-40 w-[min(90vw,340px)] origin-top-right rounded-xl border border-border/90 bg-surface p-4 shadow-[0_14px_32px_-8px_rgba(17,34,51,0.14),0_2px_6px_-1px_rgba(17,34,51,0.06)]"
              >
                <div class="flex items-center justify-between border-b border-border/80 pb-2.5">
                  <p class="text-sm font-semibold text-navy">Hoạt động học tập</p>
                  <RouterLink
                    :to="{ name: 'learning-history' }"
                    class="text-xs font-semibold text-teal transition-colors hover:text-teal-dark hover:underline"
                    @click="notificationsOpen = false"
                  >
                    Xem tất cả
                  </RouterLink>
                </div>

                <div v-if="loadingActivities" class="py-4 text-center text-xs text-muted">
                  Đang tải hoạt động...
                </div>

                <ul v-else-if="recentActivities.length" class="mt-2 divide-y divide-border/70">
                  <li v-for="item in recentActivities" :key="item.id" class="py-2.5">
                    <RouterLink
                      :to="{ name: 'course-detail', params: { id: item.course?.id || '' } }"
                      class="group block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
                      @click="notificationsOpen = false"
                    >
                      <p class="line-clamp-1 text-sm font-medium text-navy transition-colors group-hover:text-teal">
                        {{ item.course?.title || 'Khóa học' }}
                      </p>
                      <div class="mt-1 flex items-center justify-between gap-2 text-xs text-muted">
                        <span class="min-w-0 truncate">{{ item.lesson?.title || 'Bài học' }}</span>
                        <span v-if="item.createdAt" class="shrink-0 tabular-nums text-slate-600">
                          {{ formatActivityTime(item.createdAt) }}
                        </span>
                      </div>
                    </RouterLink>
                  </li>
                </ul>

                <p v-else class="py-3 text-sm text-muted">Chưa có hoạt động học tập nào.</p>
              </div>
            </Transition>
          </div>

          <!-- Account Dropdown -->
          <div ref="accountContainerRef" class="relative">
            <button
              ref="accountButtonRef"
              type="button"
              class="flex items-center gap-2 rounded-xl border border-transparent px-1.5 py-1 transition-[background-color,border-color,transform] duration-150 hover:border-border/80 hover:bg-subtle/75 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
              aria-label="Mở menu tài khoản"
              :aria-expanded="accountOpen"
              @click="accountOpen = !accountOpen; notificationsOpen = false"
            >
              <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-semibold text-white">
                {{ initials }}
              </span>
              <span
                class="hidden max-w-[120px] truncate text-sm font-semibold text-navy sm:block"
                :title="fullName"
              >
                {{ shortName }}
              </span>
              <ChevronDown
                :class="[
                  'hidden shrink-0 text-muted transition-transform duration-200 sm:block',
                  accountOpen ? 'rotate-180 text-navy' : '',
                ]"
                :size="14"
                aria-hidden="true"
              />
            </button>

            <Transition name="es-header-popover">
              <div
                v-if="accountOpen"
                class="absolute right-0 top-11 z-40 w-64 origin-top-right rounded-xl border border-border/90 bg-surface p-2 shadow-[0_14px_32px_-8px_rgba(17,34,51,0.14),0_2px_6px_-1px_rgba(17,34,51,0.06)]"
              >
                <p class="border-b border-border/80 px-3 py-2 text-xs text-muted">
                  {{ fullName }} · <strong class="text-navy">{{ roleName }}</strong>
                </p>

                <RouterLink
                  :to="{ name: dashboardRouteName }"
                  class="mt-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-navy transition-colors duration-150 hover:bg-subtle"
                  @click="accountOpen = false"
                >
                  <LayoutDashboard :size="15" aria-hidden="true" />
                  <span>{{ isLearner ? 'Không gian học tập' : 'Không gian quản lý' }}</span>
                </RouterLink>

                <template v-if="isLearner">
                  <RouterLink
                    :to="{ name: 'user-profile' }"
                    class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                    @click="accountOpen = false"
                  >
                    <UserRound :size="15" aria-hidden="true" />
                    <span>Hồ sơ cá nhân</span>
                  </RouterLink>
                  <RouterLink
                    :to="{ name: 'learning-progress' }"
                    class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                    @click="accountOpen = false"
                  >
                    <BookOpen :size="15" aria-hidden="true" />
                    <span>Khóa học của tôi</span>
                  </RouterLink>
                  <RouterLink
                    :to="{ name: 'learning-history' }"
                    class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                    @click="accountOpen = false"
                  >
                    <History :size="15" aria-hidden="true" />
                    <span>Lịch sử học tập</span>
                  </RouterLink>
                  <RouterLink
                    v-if="commerceState.marketplaceEnabled"
                    :to="{ name: 'order-history' }"
                    class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                    @click="accountOpen = false"
                  >
                    <ReceiptText :size="15" aria-hidden="true" />
                    <span>Lịch sử mua hàng</span>
                  </RouterLink>
                  <RouterLink
                    :to="{ name: 'provider-application' }"
                    class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                    @click="accountOpen = false"
                  >
                    <UserPlus :size="15" aria-hidden="true" />
                    <span>Đăng ký nhà cung cấp</span>
                  </RouterLink>
                </template>

                <RouterLink
                  v-else-if="isProvider"
                  :to="{ name: 'provider-dashboard' }"
                  class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-navy transition-colors duration-150 hover:bg-subtle"
                  @click="accountOpen = false"
                >
                  <GraduationCap :size="15" aria-hidden="true" />
                  <span>Quản lý khóa học</span>
                </RouterLink>

                <button
                  type="button"
                  class="mt-1 w-full rounded-lg border-t border-border/80 px-3 py-2 text-left text-sm text-muted transition-colors duration-150 hover:bg-subtle hover:text-navy"
                  @click="endSession"
                >
                  Đăng xuất
                </button>
              </div>
            </Transition>
          </div>
        </template>
      </div>
    </div>

    <!-- Mobile Navigation Drawer -->
    <Transition name="es-mobile-nav">
      <div v-if="mobileOpen" class="border-t border-border/80 bg-surface px-4 py-4 shadow-md lg:hidden">
        <nav class="grid grid-cols-2 gap-2" aria-label="Menu di động">
          <RouterLink
            :to="{ name: 'home' }"
            :aria-current="isNavActive('home') ? 'page' : undefined"
            :class="[
              'flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm transition-colors duration-150',
              isNavActive('home') ? 'bg-teal/10 font-semibold text-teal-dark' : 'font-medium text-navy hover:bg-subtle',
            ]"
            @click="mobileOpen = false"
          >
            Khám phá
          </RouterLink>
          <RouterLink
            :to="{ name: 'course-catalog' }"
            :aria-current="isNavActive('courses') ? 'page' : undefined"
            :class="[
              'flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm transition-colors duration-150',
              isNavActive('courses') ? 'bg-teal/10 font-semibold text-teal-dark' : 'font-medium text-navy hover:bg-subtle',
            ]"
            @click="mobileOpen = false"
          >
            Khóa học
          </RouterLink>
          <RouterLink
            :to="{ name: 'material-catalog' }"
            :aria-current="isNavActive('materials') ? 'page' : undefined"
            :class="[
              'flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm transition-colors duration-150',
              isNavActive('materials') ? 'bg-teal/10 font-semibold text-teal-dark' : 'font-medium text-navy hover:bg-subtle',
            ]"
            @click="mobileOpen = false"
          >
            Tài liệu học tập
          </RouterLink>
          <RouterLink
            v-if="isAuthenticated && !isLearner"
            :to="{ name: dashboardRouteName }"
            class="flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm font-semibold text-teal hover:bg-subtle"
            @click="mobileOpen = false"
          >
            Không gian quản lý
          </RouterLink>
          <RouterLink
            v-if="isAuthenticated && isLearner"
            :to="{ name: 'user-dashboard' }"
            :aria-current="isNavActive('my-courses') ? 'page' : undefined"
            :class="[
              'flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm transition-colors duration-150',
              isNavActive('my-courses') ? 'bg-teal/10 font-semibold text-teal-dark' : 'font-medium text-navy hover:bg-subtle',
            ]"
            @click="mobileOpen = false"
          >
            Học tập của tôi
          </RouterLink>
          <RouterLink
            v-if="isAuthenticated && isLearner"
            :to="{ name: 'course-recommendations' }"
            :aria-current="isNavActive('recommendations') ? 'page' : undefined"
            :class="[
              'flex min-h-[42px] items-center rounded-lg px-3 py-2 text-sm transition-colors duration-150',
              isNavActive('recommendations') ? 'bg-teal/10 font-semibold text-teal-dark' : 'font-medium text-navy hover:bg-subtle',
            ]"
            @click="mobileOpen = false"
          >
            Gợi ý
          </RouterLink>
        </nav>

        <div v-if="!isAuthenticated" class="mt-4 flex gap-2 border-t border-border/80 pt-3">
          <RouterLink
            :to="{ name: 'login' }"
            class="ui-button ui-button--outline ui-button--sm flex-1 text-center active:scale-[0.97]"
            @click="mobileOpen = false"
          >
            Đăng nhập
          </RouterLink>
          <RouterLink
            :to="{ name: 'register' }"
            class="ui-button ui-button--primary ui-button--sm flex-1 text-center active:scale-[0.97]"
            @click="mobileOpen = false"
          >
            Đăng ký
          </RouterLink>
        </div>
      </div>
    </Transition>

    <Transition name="es-toast">
      <div
        v-if="feedback || commerceState.toastMessage"
        class="fixed bottom-4 right-4 z-50 flex max-w-sm items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-navy shadow-[0_14px_32px_-8px_rgba(17,34,51,0.16)]"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <span class="leading-snug">{{ feedback || commerceState.toastMessage }}</span>
        <button
          type="button"
          class="shrink-0 font-semibold text-teal hover:underline"
          @click="feedback ? dismissFeedback() : dismissCommerceToast()"
        >
          Đóng
        </button>
      </div>
    </Transition>
  </header>
</template>

<style scoped>
.es-header-popover-enter-active,
.es-header-popover-leave-active {
  transition:
    opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

.es-header-popover-enter-from,
.es-header-popover-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .es-header-popover-enter-active,
  .es-header-popover-leave-active {
    transition: opacity 100ms linear;
  }

  .es-header-popover-enter-from,
  .es-header-popover-leave-to {
    transform: none;
  }
}
</style>
