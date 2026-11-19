<script setup>
import UserFooter from '@/components/user/UserFooter.vue'
import UserHeader from '@/components/user/UserHeader.vue'
import { getUserDemoNotice } from '@/service/userService'
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-navy">
    <UserHeader />
    <div class="mx-auto w-full max-w-7xl px-4 pt-4 sm:px-6 lg:px-8">
      <p class="rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-xs leading-5 text-muted" role="note">{{ getUserDemoNotice() }}</p>
    </div>
    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <RouterView />
    </main>
    <UserFooter />
  </div>
</template>
