<script setup>
import { computed } from 'vue'
import { ArrowLeft, Download, FileText, LockKeyhole } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { getPublicCourse, getPublicMaterial } from '@/service/userService'

const route = useRoute()
const material = computed(() => getPublicMaterial(String(route.params.id)))
const course = computed(() => material.value ? getPublicCourse(material.value.courseId) : null)
const kind = computed(() => {
  if (!material.value) return 'unsupported'
  const mime = material.value.mimeType || ''
  if (mime === 'application/pdf' || material.value.format === 'PDF') return 'pdf'
  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  if (typeof material.value.textContent === 'string' && material.value.textContent.trim()) return 'text'
  return 'unsupported'
})
</script>

<template>
  <div v-if="!material" class="rounded-2xl border border-slate-200 bg-white p-8 text-center"><h1 class="text-xl font-bold text-navy">Không tìm thấy tài liệu</h1><p class="mt-2 text-sm text-muted">Tài liệu không tồn tại hoặc chưa được phép truy cập.</p><RouterLink :to="{ name: 'material-catalog' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại thư viện</RouterLink></div>
  <div v-else class="space-y-5">
    <RouterLink :to="{ name: 'material-catalog' }" class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Thư viện tài liệu</RouterLink>
    <section class="grid gap-5 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
      <article class="h-fit rounded-2xl border border-slate-200 bg-white p-5">
        <span class="flex size-11 items-center justify-center rounded-xl bg-accent/10 text-accent"><FileText :size="20" aria-hidden="true" /></span>
        <h1 class="mt-4 text-xl font-bold text-navy">{{ material.title }}</h1>
        <p class="mt-2 text-sm leading-6 text-muted">{{ material.description }}</p>
        <dl class="mt-5 space-y-3 text-sm">
          <div><dt class="text-xs text-muted">Loại / định dạng</dt><dd class="mt-1 text-navy">{{ material.type }} · {{ material.format }}</dd></div>
          <div><dt class="text-xs text-muted">Dung lượng</dt><dd class="mt-1 text-navy">{{ material.sizeBytes ? `${Math.round(material.sizeBytes / 1024)} KB` : 'Chưa có dữ liệu' }}</dd></div>
          <div><dt class="text-xs text-muted">Khóa học</dt><dd class="mt-1 text-navy">{{ course?.title || 'Chưa có thông tin' }}</dd></div>
          <div><dt class="text-xs text-muted">Người cung cấp</dt><dd class="mt-1 text-navy">{{ material.provider }}</dd></div>
        </dl>
        <p v-if="!material.isAccessible" class="mt-4 flex items-center gap-2 rounded-lg bg-background p-3 text-xs text-muted"><LockKeyhole :size="15" aria-hidden="true" /> Chưa có quyền truy cập tài liệu.</p>
      </article>
      <section class="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
        <div class="flex flex-wrap items-center justify-between gap-3"><h2 class="font-bold text-navy">Xem trước tài liệu</h2><a v-if="material.fileUrl && material.isAccessible" :href="material.fileUrl" :download="material.title" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white"><Download :size="14" aria-hidden="true" /> Tải / mở tệp</a></div>
        <img v-if="material.fileUrl && kind === 'image'" :src="material.fileUrl" :alt="material.title" class="mt-4 max-h-[70vh] w-full rounded-xl object-contain">
        <iframe v-else-if="material.fileUrl && kind === 'pdf'" :src="material.fileUrl" :title="`Xem trước ${material.title}`" referrerpolicy="no-referrer" class="mt-4 h-[min(70vh,680px)] w-full rounded-xl border border-slate-200"></iframe>
        <video v-else-if="material.fileUrl && kind === 'video'" :src="material.fileUrl" controls class="mt-4 max-h-[70vh] w-full rounded-xl bg-navy"></video>
        <article v-else-if="kind === 'text'" class="mt-4 max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-background p-5 text-sm leading-7 text-navy">{{ material.textContent }}</article>
        <div v-else class="mt-4 flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-background p-6 text-center">
          <LockKeyhole :size="23" class="text-muted" aria-hidden="true" />
          <p class="mt-3 font-semibold text-navy">{{ material.isAccessible ? 'Chưa có tệp thực tế để xem trước' : 'Bạn chưa có quyền truy cập' }}</p>
          <p class="mt-1 max-w-md text-sm leading-6 text-muted">{{ material.fileUrl ? 'Định dạng này chưa được hỗ trợ xem trước.' : 'Backend chưa cung cấp URL tệp. Không tạo nút tải xuống hoặc nội dung giả.' }}</p>
        </div>
      </section>
    </section>
  </div>
</template>
