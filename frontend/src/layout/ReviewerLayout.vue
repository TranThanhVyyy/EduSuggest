<script setup>
import { ref } from 'vue'
import ReviewerHeader from '@/components/reviewer/ReviewerHeader.vue'
import ReviewerSidebar from '@/components/reviewer/ReviewerSidebar.vue'

const sidebarCollapsed = ref(false)
const mobileNavigationOpen = ref(false)
</script>

<template>
  <div class="min-h-screen bg-background text-navy lg:flex">
    <ReviewerSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileNavigationOpen"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @close-mobile="mobileNavigationOpen = false"
    />

    <div class="flex min-h-screen min-w-0 flex-1 flex-col">
      <ReviewerHeader @toggle-navigation="mobileNavigationOpen = !mobileNavigationOpen" />

      <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <RouterView />
      </main>

      <footer class="mt-auto border-t border-border/70 bg-surface/60 px-4 py-3.5 sm:px-6 lg:px-10">
        <div class="mx-auto flex max-w-6xl items-center justify-between text-xs text-slate-500">
          <span>EduSuggest</span>
          <span>Khu vực chuyên gia kiểm duyệt</span>
        </div>
      </footer>
    </div>
  </div>
</template>
