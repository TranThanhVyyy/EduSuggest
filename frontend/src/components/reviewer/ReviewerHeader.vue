<script setup>
import { computed, ref } from 'vue'
import { Bell, ChevronDown } from 'lucide-vue-next'
import { getReviewerNotifications, getReviewerProfile } from '@/service/reviewerService'

const notificationsOpen = ref(false)
const notifications = getReviewerNotifications()
const profile = getReviewerProfile()
const unreadCount = computed(() => notifications.filter((notification) => !notification.read).length)
</script>

<template>
  <header class="relative z-10 flex min-h-20 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-7">
    <div class="min-w-0">
      <p class="hidden text-xs font-medium text-muted sm:block">EduSuggest / Người kiểm duyệt</p>
      <h1 class="truncate text-lg font-bold tracking-tight text-navy sm:mt-1 sm:text-xl">
        {{ $route.meta.title || 'Không gian kiểm duyệt' }}
      </h1>
    </div>

    <div class="flex shrink-0 items-center gap-2 sm:gap-4">
      <div class="relative">
        <button
          type="button"
          class="relative flex size-10 items-center justify-center rounded-xl text-muted transition hover:bg-background hover:text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :aria-expanded="notificationsOpen"
          aria-label="Thông báo kiểm duyệt"
          @click="notificationsOpen = !notificationsOpen"
        >
          <Bell :size="19" aria-hidden="true" />
          <span v-if="unreadCount" class="absolute right-2 top-2 size-2 rounded-full bg-accent" aria-label="Thông báo chưa đọc"></span>
        </button>

        <div v-if="notificationsOpen" class="absolute right-0 top-12 z-30 w-[min(20rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-3 shadow-lg">
          <div class="flex items-center justify-between px-2 py-1">
            <h2 class="text-sm font-bold text-navy">Thông báo</h2>
            <span class="text-xs text-muted">{{ unreadCount }} mới</span>
          </div>
          <ul class="mt-2 divide-y divide-slate-100">
            <li v-for="notification in notifications" :key="notification.id" class="px-2 py-3">
              <p class="text-sm font-semibold text-navy">{{ notification.title }}</p>
              <p class="mt-1 text-xs leading-5 text-muted">{{ notification.detail }}</p>
            </li>
          </ul>
        </div>
      </div>

      <RouterLink :to="{ name: 'reviewer-profile' }" class="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-background focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
        <span class="flex size-9 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
          {{ profile.fullName.split(' ').slice(-1)[0].slice(0, 1) }}
        </span>
        <span class="hidden text-left sm:block">
          <span class="block max-w-36 truncate text-sm font-semibold text-navy">{{ profile.fullName }}</span>
          <span class="block text-xs text-muted">Người kiểm duyệt</span>
        </span>
        <ChevronDown class="hidden text-muted sm:block" :size="15" aria-hidden="true" />
        <span class="sr-only">Mở hồ sơ cá nhân</span>
      </RouterLink>
    </div>
  </header>
</template>
