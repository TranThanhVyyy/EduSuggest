<script setup>
import { computed } from 'vue'
import { ArrowLeft, BookOpen, Eye, FileText, GraduationCap, Users } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import ResourcePreview from '@/components/reviewer/ResourcePreview.vue'
import StatusBadge from '@/components/reviewer/StatusBadge.vue'
import { getAdminRecord } from '@/service/adminService'

const route = useRoute()
const resource = computed(() => route.meta.adminResource)
const detailState = computed(() => {
  try {
    return { record: getAdminRecord(resource.value, String(route.params.id)), error: '' }
  } catch (error) {
    return {
      record: null,
      error: error instanceof Error ? error.message : 'Không thể tải nội dung.',
    }
  }
})
const detail = computed(() => detailState.value.record)
const detailError = computed(() => detailState.value.error)
const listRoute = computed(() => ({
  name: {
    courses: 'admin-courses',
    lessons: 'admin-courses',
    materials: 'admin-materials',
  }[resource.value] || 'admin-dashboard',
}))
const heading = computed(() => ({
  courses: 'Chi tiết khóa học đã duyệt',
  lessons: 'Chi tiết bài học đã duyệt',
  materials: 'Chi tiết tài liệu đã duyệt',
}[resource.value] || 'Chi tiết nội dung'))
const visibilityLabel = computed(() => detail.value?.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn')

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
</script>

<template>
  <div class="space-y-5">
    <RouterLink :to="listRoute" class="inline-flex items-center gap-2 text-sm font-semibold text-muted hover:text-primary">
      <ArrowLeft :size="16" aria-hidden="true" /> Quay lại danh sách
    </RouterLink>

    <EmptyState v-if="!detail" title="Không tìm thấy nội dung" :description="detailError || 'Nội dung có thể không tồn tại hoặc chưa được Reviewer phê duyệt.'" />

    <template v-else>
      <section class="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="min-w-0">
          <p class="text-sm text-muted">{{ heading }}</p>
          <h2 class="mt-1 break-words text-2xl font-bold tracking-tight text-navy">{{ detail.title }}</h2>
          <p class="mt-2 text-sm text-muted">Mã: {{ detail.id }} · Ngày duyệt: {{ formatDate(detail.approvedAt) }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :status="detail.reviewStatus" />
          <span class="inline-flex items-center gap-1 rounded-full bg-background px-2.5 py-1 text-xs font-semibold text-muted">
            <Eye :size="13" aria-hidden="true" /> {{ visibilityLabel }}
          </span>
        </div>
      </section>

      <template v-if="resource === 'courses'">
        <section class="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
          <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <h3 class="font-bold text-navy">Thông tin khóa học</h3>
            <p class="mt-3 whitespace-pre-line text-sm leading-7 text-muted">{{ detail.description }}</p>
            <dl class="mt-5 grid gap-4 sm:grid-cols-2">
              <div><dt class="text-xs text-muted">Danh mục</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ detail.category }}</dd></div>
              <div><dt class="text-xs text-muted">Người cung cấp</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ detail.providerName }}</dd></div>
              <div><dt class="text-xs text-muted">Reviewer phụ trách</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ detail.reviewerName }}</dd></div>
              <div><dt class="text-xs text-muted">Ngày gửi</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ formatDate(detail.submittedAt) }}</dd></div>
              <div><dt class="text-xs text-muted">Số bài học</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ detail.lessonCount }}</dd></div>
              <div><dt class="text-xs text-muted">Lượt đăng ký</dt><dd class="mt-1 text-sm font-semibold text-navy">{{ Number(detail.enrollments).toLocaleString('vi-VN') }}</dd></div>
            </dl>
            <h4 class="mt-6 text-sm font-bold text-navy">Mục tiêu khóa học</h4>
            <ul class="mt-2 space-y-2">
              <li v-for="objective in detail.objectives" :key="objective" class="text-sm leading-6 text-muted">• {{ objective }}</li>
            </ul>
            <h4 class="mt-5 text-sm font-bold text-navy">Đối tượng học viên</h4>
            <p class="mt-2 text-sm leading-6 text-muted">{{ detail.audience }}</p>
          </article>
          <aside class="space-y-4">
            <section class="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 class="flex items-center gap-2 font-bold text-navy"><Users :size="17" class="text-primary" aria-hidden="true" /> Người cung cấp và Reviewer</h3>
              <p class="mt-4 text-sm font-semibold text-navy">{{ detail.providerName }}</p>
              <p class="mt-1 text-xs text-muted">Người cung cấp · {{ detail.providerId }}</p>
              <p class="mt-4 border-t border-slate-100 pt-4 text-sm font-semibold text-navy">{{ detail.reviewerName }}</p>
              <p class="mt-1 text-xs text-muted">Reviewer · {{ detail.reviewerId }}</p>
              <p class="mt-4 border-t border-slate-100 pt-4 text-xs text-muted">Ngày phê duyệt</p>
              <p class="mt-1 text-sm font-semibold text-navy">{{ formatDate(detail.approvedAt) }}</p>
            </section>
            <section class="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 class="flex items-center gap-2 font-bold text-navy"><GraduationCap :size="17" class="text-primary" aria-hidden="true" /> Ảnh đại diện</h3>
              <ResourcePreview v-if="detail.imageUrl" class="mt-3" :resource="{ type: 'image', url: detail.imageUrl, name: detail.title }" />
              <p v-else class="mt-3 rounded-xl bg-background p-4 text-sm text-muted" role="status">Khóa học chưa có ảnh đại diện thực tế.</p>
            </section>
          </aside>
        </section>

        <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <h3 class="flex items-center gap-2 font-bold text-navy"><BookOpen :size="18" class="text-primary" aria-hidden="true" /> Cấu trúc bài học</h3>
          <div v-if="detail.lessons.length" class="mt-4 divide-y divide-slate-100">
            <RouterLink v-for="lesson in detail.lessons" :key="lesson.id" :to="{ name: 'admin-lesson-detail', params: { id: lesson.id } }" class="flex flex-wrap items-center justify-between gap-3 py-3 hover:bg-background/70">
              <span>
                <span class="block text-sm font-semibold text-navy">{{ lesson.order }}. {{ lesson.title }}</span>
                <span class="mt-1 block text-xs text-muted">{{ lesson.chapter }} · {{ lesson.duration }} · {{ lesson.contentType }}</span>
              </span>
              <span class="text-xs font-semibold text-primary">Xem bài học</span>
            </RouterLink>
          </div>
          <p v-else class="mt-3 text-sm text-muted">Chưa có dữ liệu bài học liên quan.</p>
        </section>

        <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <h3 class="flex items-center gap-2 font-bold text-navy"><FileText :size="18" class="text-primary" aria-hidden="true" /> Tài liệu liên quan</h3>
          <div v-if="detail.materials.length" class="mt-4 grid gap-3 md:grid-cols-2">
            <RouterLink v-for="material in detail.materials" :key="material.id" :to="{ name: 'admin-material-detail', params: { id: material.id } }" class="rounded-xl border border-slate-200 p-4 hover:border-primary/40">
              <span class="block text-sm font-semibold text-navy">{{ material.title }}</span>
              <span class="mt-1 block text-xs text-muted">{{ material.documentType }} · {{ material.fileName }}</span>
            </RouterLink>
          </div>
          <p v-else class="mt-3 text-sm text-muted">Chưa có dữ liệu tài liệu liên quan.</p>
        </section>
      </template>

      <template v-else-if="resource === 'lessons'">
        <section class="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
          <article class="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <div>
              <h3 class="font-bold text-navy">Nội dung bài học</h3>
              <p class="mt-2 text-sm leading-6 text-muted">{{ detail.courseTitle }} · {{ detail.chapter }} · Bài {{ detail.order }}</p>
            </div>
            <ResourcePreview :resource="detail.content" />
          </article>
          <aside class="space-y-4">
            <section class="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 class="font-bold text-navy">Thông tin bài học</h3>
              <dl class="mt-4 space-y-3 text-sm">
                <div><dt class="text-xs text-muted">Mã bài học</dt><dd class="mt-1 font-semibold text-navy">{{ detail.id }}</dd></div>
                <div><dt class="text-xs text-muted">Thời lượng</dt><dd class="mt-1 font-semibold text-navy">{{ detail.duration }}</dd></div>
                <div><dt class="text-xs text-muted">Loại nội dung</dt><dd class="mt-1 font-semibold text-navy">{{ detail.contentType }}</dd></div>
                <div><dt class="text-xs text-muted">Trạng thái hiển thị</dt><dd class="mt-1 font-semibold text-navy">{{ visibilityLabel }}</dd></div>
                <div><dt class="text-xs text-muted">Trạng thái kiểm duyệt</dt><dd class="mt-1"><StatusBadge :status="detail.reviewStatus" /></dd></div>
              </dl>
            </section>
            <RouterLink v-if="detail.course" :to="{ name: 'admin-course-detail', params: { id: detail.course.id } }" class="block rounded-2xl border border-slate-200 bg-white p-5 hover:border-primary/40">
              <p class="text-xs text-muted">Khóa học</p>
              <p class="mt-1 text-sm font-semibold text-primary">{{ detail.course.title }}</p>
            </RouterLink>
          </aside>
        </section>
        <section class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <h3 class="font-bold text-navy">Tài liệu đính kèm</h3>
          <div v-if="detail.materials.length" class="mt-3 space-y-4">
            <article v-for="material in detail.materials" :key="material.id" class="rounded-xl border border-slate-200 p-4">
              <p class="text-sm font-semibold text-navy">{{ material.title }} · {{ material.fileName }}</p>
              <div class="mt-3"><ResourcePreview :resource="material" /></div>
            </article>
          </div>
          <p v-else class="mt-3 text-sm text-muted">Chưa có dữ liệu tài liệu đính kèm.</p>
        </section>
      </template>

      <template v-else>
        <section class="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
          <article class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <h3 class="font-bold text-navy">Xem trước tài liệu</h3>
            <p class="mt-1 text-sm text-muted">Trình xem chọn theo MIME type; nếu thiếu tệp thật, hệ thống sẽ báo rõ.</p>
            <div class="mt-4"><ResourcePreview :resource="detail" /></div>
          </article>
          <aside class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <h3 class="font-bold text-navy">Thông tin tài liệu</h3>
            <dl class="mt-4 space-y-3 text-sm">
              <div><dt class="text-xs text-muted">Loại tài liệu</dt><dd class="mt-1 font-semibold text-navy">{{ detail.documentType }}</dd></div>
              <div><dt class="text-xs text-muted">Định dạng</dt><dd class="mt-1 break-all font-semibold text-navy">{{ detail.mimeType }}</dd></div>
              <div><dt class="text-xs text-muted">Dung lượng</dt><dd class="mt-1 font-semibold text-navy">{{ Number.isFinite(detail.sizeBytes) ? `${detail.sizeBytes} B` : 'Chưa có dữ liệu' }}</dd></div>
              <div><dt class="text-xs text-muted">Người cung cấp</dt><dd class="mt-1 font-semibold text-navy">{{ detail.providerName }}</dd></div>
              <div><dt class="text-xs text-muted">Reviewer</dt><dd class="mt-1 font-semibold text-navy">{{ detail.reviewerName }}</dd></div>
              <div><dt class="text-xs text-muted">Ngày phê duyệt</dt><dd class="mt-1 font-semibold text-navy">{{ formatDate(detail.approvedAt) }}</dd></div>
              <div><dt class="text-xs text-muted">Khóa học/bài học liên quan</dt><dd class="mt-1 font-semibold text-navy">{{ detail.courseTitle || detail.lessonTitle || 'Tài liệu độc lập' }}</dd></div>
            </dl>
          </aside>
        </section>
      </template>
    </template>
  </div>
</template>
