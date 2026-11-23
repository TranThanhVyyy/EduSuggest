<script setup>
import UserFooter from '@/components/user/UserFooter.vue'
import UserHeader from '@/components/user/UserHeader.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-navy">
    <UserHeader />
    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <RouterView />
    </main>
    <UserFooter />
  </div>
</template>
