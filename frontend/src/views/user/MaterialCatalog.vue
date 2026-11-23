<script setup>
import { ref } from 'vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'

const query = ref('')

</script>

<template>
  <div class="space-y-5">
    <section class="border-b border-border pb-5"><p class="ui-eyebrow">Thư viện học tập</p><h1 class="ui-page-title mt-2">Tài liệu học tập</h1><p class="mt-2 text-sm text-muted">Tài liệu được đề xuất hiện trong chi tiết khóa học hoặc trang Gợi ý tài liệu (yêu cầu đã đăng ký khóa học).</p></section>
    <section class="max-w-2xl border-y border-border py-3">
      <EmptyState title="Chưa có API thư viện tài liệu công khai" description="Backend hiện chưa có endpoint liệt kê tài liệu công khai. Tài liệu được gợi ý theo từng khóa học đã đăng ký qua API gợi ý." />
    </section>
  </div>
</template>
