<script setup>
import { ref } from 'vue'
import ProviderHeader from '@/components/provider/ProviderHeader.vue'
import ProviderSidebar from '@/components/provider/ProviderSidebar.vue'
import { getProviderDemoNotice } from '@/service/providerService'

const sidebarCollapsed = ref(false)
const mobileNavigationOpen = ref(false)
</script>

<template>
  <div class="min-h-screen bg-background text-navy lg:flex">
    <ProviderSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileNavigationOpen"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @close-mobile="mobileNavigationOpen = false"
    />
    <div class="min-w-0 flex-1">
      <ProviderHeader @toggle-navigation="mobileNavigationOpen = !mobileNavigationOpen" />
      <main class="mx-auto w-full max-w-[1600px] space-y-4 p-4 sm:p-6 lg:p-8">
        <p class="rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-xs leading-5 text-muted" role="note">{{ getProviderDemoNotice() }}</p>
        <RouterView />
      </main>
      <footer class="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-muted sm:px-6 lg:px-8">
        EduSuggest · Khu vực người cung cấp · Dữ liệu minh họa trong phiên
      </footer>
    </div>
  </div>
</template>
