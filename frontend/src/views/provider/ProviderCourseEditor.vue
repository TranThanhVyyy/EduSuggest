<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, ArrowRight, Check } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  createProviderCourseRecord,
  loadProviderCategories,
  loadProviderCourse,
  providerErrorMessage,
  submitProviderCourseRecord,
  updateProviderCourseRecord,
} from '@/service/providerApiService'

const route = useRoute()
const router = useRouter()
const steps = ['Thông tin khóa học', 'Kiểm tra và gửi']
const categories = ref([])
const step = ref(route.meta.providerInitialStep ? 1 : 0)
const courseId = ref(String(route.params.id || ''))
const originalCourse = ref(null)
const errorMessage = ref('')
const toastMessage = ref('')
const submitConfirmOpen = ref(false)
const courseLoadError = ref('')
const form = reactive({ title: '', categoryId: '', description: '', level: '', price: null, durationMinutes: null })

const isEditable = computed(() => !originalCourse.value || [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(originalCourse.value.status))
const isResubmission = computed(() => originalCourse.value
  && [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(originalCourse.value.status))
const validationIssues = computed(() => {
  const issues = []
  if (!form.title.trim()) issues.push('Nhập tên khóa học.')
  if (!form.categoryId) issues.push('Chọn danh mục.')
  if (!originalCourse.value?.lessons?.length) issues.push('Thêm và lưu ít nhất một bài học trong mục Bài học.')
  if (originalCourse.value?.lessons?.some((lesson) => !lesson.title.trim())) issues.push('Mỗi bài học cần có tên trước khi gửi.')
  return issues
})

onMounted(async () => {
  try {
    categories.value = await loadProviderCategories()
    if (courseId.value) {
      originalCourse.value = await loadProviderCourse(courseId.value)
      Object.assign(form, {
        title: originalCourse.value.title,
        categoryId: originalCourse.value.categoryId,
        description: originalCourse.value.description,
        level: originalCourse.value.level,
        price: originalCourse.value.price,
        durationMinutes: originalCourse.value.durationMinutes,
      })
    } else if (!categories.value.length) {
      courseLoadError.value = 'Chưa có danh mục khả dụng. Hãy yêu cầu quản trị viên cấu hình danh mục trước khi tạo khóa học.'
    }
  } catch (error) {
    courseLoadError.value = providerErrorMessage(error, 'Không thể tải danh mục hoặc khóa học từ Backend.')
  }
})

async function persistCourse() {
  const payload = {
    title: form.title.trim(),
    categoryId: form.categoryId,
    description: form.description.trim(),
    level: form.level.trim(),
    price: form.price,
    durationMinutes: form.durationMinutes,
  }
  const saved = courseId.value
    ? await updateProviderCourseRecord(courseId.value, payload)
    : await createProviderCourseRecord(payload)
  courseId.value = saved.id
  originalCourse.value = await loadProviderCourse(saved.id)
  return originalCourse.value
}

async function saveDraft() {
  try {
    await persistCourse()
    errorMessage.value = ''
    toastMessage.value = 'Đã lưu thông tin khóa học trên Backend.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu bản nháp.')
  }
}

function goNext() {
  if (!form.title.trim() || !form.categoryId) {
    errorMessage.value = 'Nhập tên khóa học và chọn danh mục trước khi tiếp tục.'
    return
  }
  errorMessage.value = ''
  step.value = 1
}

async function submitForReview() {
  try {
    const saved = await persistCourse()
    await submitProviderCourseRecord(saved.id)
    toastMessage.value = isResubmission.value
      ? 'Đã gửi lại khóa học; kết quả được xử lý bởi Backend.'
      : 'Đã gửi khóa học; kết quả được xử lý bởi Backend.'
    submitConfirmOpen.value = false
    router.push({ name: 'provider-course-detail', params: { id: saved.id } })
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể gửi kiểm duyệt.')
    submitConfirmOpen.value = false
  }
}
</script>

<template>
  <div v-if="courseLoadError" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Không thể mở trình soạn khóa học</h2>
    <p class="mt-2 text-sm text-muted">{{ courseLoadError }}</p>
    <RouterLink :to="{ name: 'provider-courses' }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quay lại danh sách</RouterLink>
  </div>
  <div v-else-if="originalCourse && !isEditable" class="rounded-2xl border border-slate-200 bg-white p-6">
    <h2 class="text-xl font-bold text-navy">Khóa học hiện không thể chỉnh sửa</h2>
    <p class="mt-2 text-sm text-muted">Trạng thái hiện tại: {{ PROVIDER_STATUS_LABELS[originalCourse.status] }}. Nội dung đã gửi hoặc đã được xử lý cần tuân theo quy trình Backend.</p>
    <RouterLink :to="{ name: 'provider-course-detail', params: { id: courseId } }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Xem khóa học</RouterLink>
  </div>
  <div v-else class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">{{ originalCourse ? 'Cập nhật khóa học' : 'Tạo khóa học' }}</p>
        <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">{{ form.title || 'Khóa học mới' }}</h2>
        <p class="mt-2 text-sm text-muted">Thông tin được lưu: tên, danh mục, mô tả, trình độ, học phí và thời lượng. Bài học cần được quản lý riêng.</p>
      </div>
      <button type="button" class="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background" @click="saveDraft">Lưu bản nháp</button>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <ol class="grid gap-2 sm:grid-cols-2" aria-label="Các bước tạo khóa học">
        <li v-for="(label, index) in steps" :key="label">
          <button type="button" class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-semibold" :class="step === index ? 'bg-primary text-white' : 'bg-background text-muted'" :aria-current="step === index ? 'step' : undefined" :disabled="index > step" @click="step = index">
            <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-white/20">{{ index + 1 }}</span><span>{{ label }}</span>
          </button>
        </li>
      </ol>

      <div v-if="step === 0" class="mt-6 grid gap-4 md:grid-cols-2">
        <label class="text-sm font-semibold text-navy md:col-span-2">Tên khóa học *
          <input v-model="form.title" maxlength="255" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Tên khóa học">
        </label>
        <label class="text-sm font-semibold text-navy">Danh mục *
          <select v-model="form.categoryId" class="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
            <option value="">Chọn danh mục</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
          </select>
        </label>
        <label class="text-sm font-semibold text-navy">Thời lượng (phút)
          <input v-model.number="form.durationMinutes" type="number" min="0" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Ví dụ: 480">
        </label>
        <label class="text-sm font-semibold text-navy">Học phí
          <input v-model.number="form.price" type="number" min="0" step="0.01" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Để trống nếu chưa xác định">
        </label>
        <label class="text-sm font-semibold text-navy">Trình độ
          <input v-model="form.level" maxlength="100" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy md:col-span-2">Mô tả
          <textarea v-model="form.description" rows="5" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" placeholder="Mô tả khóa học"></textarea>
        </label>
        <p class="text-sm leading-6 text-muted md:col-span-2">Ảnh khóa học và các trường mục tiêu, đối tượng, kiến thức đầu vào, kết quả học tập hiện chưa có trường lưu hoặc API tương ứng.</p>
      </div>

      <div v-else class="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.7fr)]">
        <article class="rounded-xl border border-slate-200 p-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ categories.find((item) => item.id === form.categoryId)?.name || 'Chưa chọn danh mục' }}</p>
          <h3 class="mt-2 text-xl font-bold text-navy">{{ form.title || 'Tên khóa học' }}</h3>
          <p class="mt-3 whitespace-pre-line text-sm leading-6 text-navy">{{ form.description || 'Chưa có mô tả.' }}</p>
          <p class="mt-3 text-xs text-muted">{{ form.durationMinutes ?? 'Chưa có' }} phút · {{ form.level || 'Chưa xác định trình độ' }}</p>
          <p class="mt-1 text-xs text-muted">Học phí: {{ form.price ?? 'Chưa xác định' }}</p>
          <RouterLink v-if="courseId" :to="{ name: 'provider-lessons', params: { id: courseId } }" class="mt-4 inline-flex text-sm font-semibold text-primary hover:underline">Quản lý bài học đã lưu →</RouterLink>
          <p v-else class="mt-4 text-sm text-muted">Lưu bản nháp trước để tạo mã khóa học, sau đó có thể thêm bài học.</p>
        </article>
        <aside class="rounded-xl border border-slate-200 p-4">
          <h3 class="font-bold text-navy">Điều kiện gửi kiểm duyệt</h3>
          <ul class="mt-3 space-y-2">
            <li class="flex gap-2 text-xs" :class="form.title.trim() && form.categoryId ? 'text-accent' : 'text-muted'"><Check :size="15" aria-hidden="true" />Tên khóa học và danh mục</li>
            <li class="flex gap-2 text-xs" :class="originalCourse?.lessons?.length ? 'text-accent' : 'text-muted'"><Check :size="15" aria-hidden="true" />Ít nhất một bài học đã lưu trên Backend</li>
          </ul>
          <p class="mt-4 border-t border-slate-100 pt-3 text-xs leading-5 text-muted">Provider gửi khóa học để chuyên gia kiểm duyệt; Provider không thể tự phê duyệt hoặc công khai.</p>
        </aside>
      </div>

      <p v-if="errorMessage" class="mt-5 rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
      <div class="mt-6 flex flex-col-reverse justify-between gap-2 border-t border-slate-100 pt-4 sm:flex-row">
        <button type="button" class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-navy hover:bg-background" @click="step ? (step = 0) : router.push({ name: 'provider-courses' })"><ArrowLeft :size="16" aria-hidden="true" />{{ step ? 'Quay lại' : 'Danh sách khóa học' }}</button>
        <button v-if="step === 0" type="button" class="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90" @click="goNext">Tiếp tục <ArrowRight :size="16" aria-hidden="true" /></button>
        <button v-else type="button" class="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" :disabled="validationIssues.length > 0" @click="submitConfirmOpen = true">Gửi kiểm duyệt</button>
      </div>
    </section>

    <AdminModal :open="submitConfirmOpen" mode="confirm" :title="isResubmission ? 'Xác nhận gửi lại kiểm duyệt' : 'Xác nhận gửi kiểm duyệt'" :description="form.title || 'Khóa học chưa đặt tên'" confirm-label="Xác nhận gửi" @close="submitConfirmOpen = false" @confirm="submitForReview">
      <p>Khóa học chuyển sang chờ kiểm duyệt. Chuyên gia quyết định kết quả; thao tác này không phê duyệt hoặc công khai khóa học.</p>
    </AdminModal>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
