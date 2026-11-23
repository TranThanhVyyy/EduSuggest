<script setup>
import { ArrowLeft } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import { getPublicMaterial } from '@/service/userService'

const route = useRoute()
const material = getPublicMaterial(String(route.params.id))
</script>

<template>
  <div class="max-w-3xl">
    <RouterLink :to="{ name: 'material-catalog' }" class="inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Thư viện tài liệu</RouterLink>
    <section class="mt-5 border-y border-border py-3">
      <EmptyState :title="material ? material.title : 'Tài liệu chưa khả dụng'" :description="material ? material.description : 'Thông tin và quyền truy cập tài liệu chưa được cung cấp từ Backend.'" />
    </section>
  </div>
</template>
