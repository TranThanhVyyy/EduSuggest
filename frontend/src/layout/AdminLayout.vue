<script setup>
import { ref } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminSidebar from '@/components/admin/AdminSidebar.vue'

const sidebarCollapsed = ref(false)
const mobileNavigationOpen = ref(false)
</script>

<template>
  <div class="min-h-screen bg-background text-navy lg:flex">
    <AdminSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileNavigationOpen"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @close-mobile="mobileNavigationOpen = false"
    />
    <div class="min-w-0 flex-1">
      <AdminHeader @toggle-navigation="mobileNavigationOpen = !mobileNavigationOpen" />
      <main class="mx-auto w-full max-w-[1600px] p-4 sm:p-6 lg:p-8">
        <RouterView />
      </main>
      <footer class="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-muted sm:px-6 lg:px-8">
        EduSuggest · Trung tâm quản trị 
      </footer>
    </div>
  </div>
</template>
