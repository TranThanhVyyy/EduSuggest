<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, Eye, EyeOff } from 'lucide-vue-next'
import AdminModal from '@/components/admin/AdminModal.vue'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import PaginationControls from '@/components/reviewer/PaginationControls.vue'
import SearchInput from '@/components/reviewer/SearchInput.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getAdminVisibilityItems, setAdminVisibility } from '@/service/adminService'

const pageSize = 8
const query = ref('')
const typeFilter = ref('')
const visibilityFilter = ref('')
const currentPage = ref(1)
const expandedCourseIds = ref([])
const pendingItem = ref(null)
const modalOpen = ref(false)
const modalError = ref('')
const toastMessage = ref('')
const items = computed(() => getAdminVisibilityItems())

function matchesSearch(item, search) {
  const text = `${item.id} ${item.displayName} ${item.providerName || ''} ${item.courseTitle || ''}`.toLocaleLowerCase('vi')
  return !search || text.includes(search)
}

function matchesVisibility(item) {
  return !visibilityFilter.value || item.visibility === visibilityFilter.value
}

const courseGroups = computed(() => {
  if (typeFilter.value === 'material') return []
  const search = query.value.trim().toLocaleLowerCase('vi')

  return items.value
    .filter((item) => item.itemType === 'course')
    .map((course) => {
      const courseMatchesSearch = matchesSearch(course, search)
      const lessons = items.value
        .filter((item) => item.itemType === 'lesson' && item.courseId === course.id)
        .filter((lesson) => matchesVisibility(lesson))
        .filter((lesson) => !search || courseMatchesSearch || matchesSearch(lesson, search))
      const courseMatches = matchesSearch(course, search) && matchesVisibility(course)
      const shownAsCourse = typeFilter.value !== 'lesson' && courseMatches
      const shownByLessons = typeFilter.value !== 'course' && lessons.length > 0

      if (!shownAsCourse && !shownByLessons) return null
      return { ...course, lessons }
    })
    .filter(Boolean)
})

const materials = computed(() => {
  if (typeFilter.value === 'course' || typeFilter.value === 'lesson') return []
  const search = query.value.trim().toLocaleLowerCase('vi')
  return items.value
    .filter((item) => item.itemType === 'material')
    .filter((item) => matchesSearch(item, search) && matchesVisibility(item))
})
const filteredItems = computed(() => [
  ...courseGroups.value,
  ...materials.value,
])
const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize)))
const visibleItems = computed(() =>
  filteredItems.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize),
)

watch([query, typeFilter, visibilityFilter], () => {
  currentPage.value = 1
  expandedCourseIds.value = []
})
watch(totalPages, (pages) => { if (currentPage.value > pages) currentPage.value = pages })

function itemTypeLabel(type) {
  return { course: 'Khóa học', lesson: 'Bài học', material: 'Tài liệu' }[type] || 'Nội dung'
}

function itemDetailRoute(item) {
  return {
    course: 'admin-course-detail',
    lesson: 'admin-lesson-detail',
    material: 'admin-material-detail',
  }[item.itemType]
}

function toggleCourseLessons(courseId) {
  expandedCourseIds.value = expandedCourseIds.value.includes(courseId)
    ? expandedCourseIds.value.filter((id) => id !== courseId)
    : [...expandedCourseIds.value, courseId]
}

function requestVisibilityChange(item) {
  pendingItem.value = {
    ...item,
    nextVisibility: item.visibility === 'visible' ? 'hidden' : 'visible',
  }
  modalError.value = ''
  modalOpen.value = true
}

function confirmChange() {
  try {
    setAdminVisibility(pendingItem.value.itemType, pendingItem.value.id, pendingItem.value.nextVisibility)
    toastMessage.value = pendingItem.value.nextVisibility === 'hidden'
      ? 'Đã ẩn nội dung trong phiên làm việc.'
      : 'Đã hiển thị lại nội dung trong phiên làm việc.'
    modalOpen.value = false
    pendingItem.value = null
  } catch (error) {
    modalError.value = error instanceof Error ? error.message : 'Không thể cập nhật trạng thái hiển thị.'
  }
}
</script>

<template>
  <div class="space-y-5">
    <section>
      <p class="text-sm text-muted">Quản lý nội dung</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Trạng thái hiển thị</h2>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">Bài học được nhóm bên trong khóa học. Chỉ nội dung đã được Reviewer phê duyệt mới xuất hiện tại đây.</p>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(240px,1fr)_190px_190px]">
        <SearchInput v-model="query" label="Tìm nội dung" placeholder="Tên, mã, người cung cấp..." />
        <label class="sr-only" for="visibility-type">Lọc loại nội dung</label>
        <select id="visibility-type" v-model="typeFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Tất cả nội dung</option>
          <option value="course">Khóa học</option>
          <option value="lesson">Bài học trong khóa học</option>
          <option value="material">Tài liệu</option>
        </select>
        <label class="sr-only" for="visibility-status">Lọc trạng thái hiển thị</label>
        <select id="visibility-status" v-model="visibilityFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
          <option value="">Mọi trạng thái hiển thị</option>
          <option value="visible">Đang hiển thị</option>
          <option value="hidden">Đã ẩn</option>
        </select>
      </div>

      <div v-if="visibleItems.length" class="overflow-x-auto">
        <table class="w-full min-w-[820px] text-left text-sm">
          <thead class="bg-background text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="px-4 py-3 font-semibold">Nội dung</th>
              <th scope="col" class="px-4 py-3 font-semibold">Loại</th>
              <th scope="col" class="px-4 py-3 font-semibold">Người cung cấp</th>
              <th scope="col" class="px-4 py-3 font-semibold">Kiểm duyệt</th>
              <th scope="col" class="px-4 py-3 font-semibold">Hiển thị</th>
              <th scope="col" class="px-4 py-3 text-right font-semibold">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="item in visibleItems" :key="`${item.itemType}-${item.id}`">
              <tr>
                <th scope="row" class="max-w-72 px-4 py-3.5 font-semibold text-navy">
                  <div class="flex items-start gap-2">
                    <button
                      v-if="item.itemType === 'course'"
                      type="button"
                      class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-primary/10 hover:text-primary"
                      :aria-label="`${expandedCourseIds.includes(item.id) ? 'Thu gọn' : 'Mở'} bài học của ${item.displayName}`"
                      :aria-expanded="expandedCourseIds.includes(item.id)"
                      @click="toggleCourseLessons(item.id)"
                    >
                      <ChevronDown :size="16" :class="expandedCourseIds.includes(item.id) ? 'rotate-180' : ''" aria-hidden="true" />
                    </button>
                    <RouterLink :to="{ name: itemDetailRoute(item), params: { id: item.id } }" class="line-clamp-2 hover:text-primary">{{ item.displayName }}</RouterLink>
                  </div>
                  <span class="mt-1 block text-xs font-normal text-muted">{{ item.id }}<template v-if="item.itemType === 'course'"> · {{ item.lessons.length }} bài học có dữ liệu</template></span>
                </th>
                <td class="px-4 py-3.5 text-muted">{{ itemTypeLabel(item.itemType) }}</td>
                <td class="px-4 py-3.5 text-muted">{{ item.providerName || 'Chưa có dữ liệu' }}</td>
                <td class="px-4 py-3.5"><span class="rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">Đã phê duyệt</span></td>
                <td class="px-4 py-3.5"><span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="item.visibility === 'visible' ? 'bg-accent/10 text-accent' : 'bg-background text-muted'">{{ item.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn' }}</span></td>
                <td class="px-4 py-3.5 text-right">
                  <button type="button" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:border-primary hover:text-primary" @click="requestVisibilityChange(item)">
                    <EyeOff v-if="item.visibility === 'visible'" :size="14" aria-hidden="true" />
                    <Eye v-else :size="14" aria-hidden="true" />
                    {{ item.visibility === 'visible' ? 'Ẩn' : 'Hiển thị lại' }}
                  </button>
                </td>
              </tr>
              <tr v-if="item.itemType === 'course' && expandedCourseIds.includes(item.id)" class="bg-background/70">
                <td colspan="6" class="px-4 py-4">
                  <div v-if="item.lessons.length" class="space-y-2">
                    <div v-for="lesson in item.lessons" :key="lesson.id" class="grid gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
                      <div class="min-w-0">
                        <RouterLink :to="{ name: 'admin-lesson-detail', params: { id: lesson.id } }" class="text-sm font-semibold text-navy hover:text-primary">{{ lesson.order }}. {{ lesson.title }}</RouterLink>
                        <p class="mt-1 text-xs text-muted">{{ lesson.id }} · {{ lesson.chapter }} · {{ lesson.duration }} · {{ lesson.contentType }}</p>
                      </div>
                      <span class="w-fit rounded-full px-2.5 py-1 text-xs font-semibold" :class="lesson.visibility === 'visible' ? 'bg-accent/10 text-accent' : 'bg-background text-muted'">{{ lesson.visibility === 'visible' ? 'Đang hiển thị' : 'Đã ẩn' }}</span>
                      <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:border-primary hover:text-primary" @click="requestVisibilityChange(lesson)">
                        <EyeOff v-if="lesson.visibility === 'visible'" :size="14" aria-hidden="true" />
                        <Eye v-else :size="14" aria-hidden="true" />
                        {{ lesson.visibility === 'visible' ? 'Ẩn bài học' : 'Hiển thị lại' }}
                      </button>
                    </div>
                  </div>
                  <p v-else class="rounded-xl border border-dashed border-slate-200 bg-white p-4 text-sm text-muted">Khóa học này chưa có bài học phù hợp với bộ lọc hoặc chưa có bài học được duyệt.</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="Không có nội dung phù hợp" description="Thay đổi từ khóa hoặc bộ lọc để xem thêm nội dung đã duyệt." />
      <PaginationControls v-if="filteredItems.length" v-model="currentPage" :total-pages="totalPages" :total-items="filteredItems.length" />
    </section>

    <AdminModal
      :open="modalOpen"
      mode="confirm"
      :title="pendingItem?.nextVisibility === 'hidden' ? 'Xác nhận ẩn nội dung' : 'Xác nhận hiển thị nội dung'"
      :description="pendingItem?.displayName || pendingItem?.title || ''"
      :confirm-label="pendingItem?.nextVisibility === 'hidden' ? 'Ẩn nội dung' : 'Hiển thị lại'"
      :error="modalError"
      @close="modalOpen = false"
      @confirm="confirmChange"
    >
      <p>Trạng thái kiểm duyệt vẫn là <strong>Đã phê duyệt</strong>. Thao tác này chỉ thay đổi khả năng hiển thị trên hệ thống.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
