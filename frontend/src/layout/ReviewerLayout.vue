<script setup>
import ReviewerHeader from '@/components/reviewer/ReviewerHeader.vue'
import ReviewerSidebar from '@/components/reviewer/ReviewerSidebar.vue'
</script>

<template>
  <div class="min-h-screen bg-background text-navy lg:grid lg:grid-cols-[260px_minmax(0,1fr)]">
    <ReviewerSidebar />
    <div class="min-w-0">
      <ReviewerHeader />
      <main class="mx-auto w-full max-w-[1500px] p-4 sm:p-6 lg:p-8">
        <RouterView />
      </main>
      <footer class="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-muted sm:px-6 lg:px-8">
        EduSuggest · Không gian kiểm duyệt nội dung học tập
      </footer>
    </div>
  </div>
</template>
