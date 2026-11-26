<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  CheckCircle2,
  ExternalLink,
  FileText,
  GraduationCap,
  ImagePlus,
  Paperclip,
  Plus,
  RefreshCw,
  Save,
  Send,
  Trash2,
  Upload,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import AdminModal from '@/components/admin/AdminModal.vue'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import {
  PROVIDER_STATUS,
  PROVIDER_STATUS_LABELS,
  createProviderCourseRecord,
  createProviderLesson,
  createProviderMaterial,
  deleteProviderLesson,
  deleteProviderMaterial,
  loadProviderCategories,
  loadProviderCourse,
  providerErrorMessage,
  submitProviderCourseRecord,
  updateProviderCourseRecord,
  updateProviderLesson,
  uploadProviderCourseCover,
  uploadStandaloneMaterialFile,
} from '@/service/providerApiService'
import { openMaterialFile } from '@/service/materialFileService'

const route = useRoute()
const router = useRouter()
const steps = ['1. Thông tin khóa học', '2. Bài học', '3. Xem trước & Gửi duyệt']
const categories = ref([])
const step = ref(route.meta.providerInitialStep ? 2 : 0)
const courseId = ref(String(route.params.id || ''))
const originalCourse = ref(null)
const errorMessage = ref('')
const toastMessage = ref('')
const submitConfirmOpen = ref(false)
const courseLoadError = ref('')
const saving = ref(false)
const savingLessons = ref(false)
const submitting = ref(false)
const uploadingCover = ref(false)
const coverError = ref('')
const isDraggingCover = ref(false)
const coverInputRef = ref(null)

const form = reactive({
  title: '',
  categoryId: '',
  description: '',
  coverImageUrl: '',
  coverImagePath: '',
  level: '',
  price: null,
  durationMinutes: null,
})

const lessonDrafts = ref([])
const activeMaterialLessonId = ref('')
const savingMaterial = ref(false)
const selectedMaterialFile = ref(null)
const openingMaterialId = ref('')
const materialForm = reactive({
  title: '',
  documentType: 'PDF',
  fileUrl: '',
  description: '',
})

function syncLessonsFromCourse(course) {
  lessonDrafts.value = (course?.lessons || []).map((lesson, idx) => ({
    id: lesson.id,
    title: lesson.title || '',
    durationMinutes: lesson.durationMinutes ?? null,
    videoUrl: lesson.video?.url || '',
    content: lesson.content || '',
    thuTu: lesson.thuTu ?? idx + 1,
    materials: lesson.materials || [],
    dirty: false,
  }))
}

const isEditable = computed(() => !originalCourse.value || [
  PROVIDER_STATUS.draft,
  PROVIDER_STATUS.rejected,
  PROVIDER_STATUS.changesRequested,
].includes(originalCourse.value.status))

const isResubmission = computed(() => originalCourse.value
  && [PROVIDER_STATUS.rejected, PROVIDER_STATUS.changesRequested].includes(originalCourse.value.status))

const savedLessonsCount = computed(() => originalCourse.value?.lessons?.length || 0)

const validationIssues = computed(() => {
  const issues = []
  if (!form.title.trim()) issues.push('Tên khóa học không được để trống.')
  if (!form.categoryId) issues.push('Chưa chọn danh mục khóa học.')
  if (!savedLessonsCount.value) {
    issues.push('Khóa học cần ít nhất một bài học được lưu ở Bước 2.')
  }
  if (originalCourse.value?.lessons?.some((lesson) => !lesson.title.trim())) {
    issues.push('Mỗi bài học cần có tiêu đề rõ ràng trước khi gửi duyệt.')
  }
  return issues
})

const selectedCategoryName = computed(() => {
  return categories.value.find((cat) => String(cat.id) === String(form.categoryId))?.name || 'Chưa phân loại'
})

onMounted(async () => {
  try {
    categories.value = await loadProviderCategories()
    if (courseId.value) {
      originalCourse.value = await loadProviderCourse(courseId.value)
      Object.assign(form, {
        title: originalCourse.value.title || '',
        categoryId: originalCourse.value.categoryId || '',
        description: originalCourse.value.description || '',
        coverImageUrl: originalCourse.value.coverImageUrl || '',
        coverImagePath: originalCourse.value.rawCoverImageUrl || '',
        level: originalCourse.value.level || '',
        price: originalCourse.value.price,
        durationMinutes: originalCourse.value.durationMinutes,
      })
      syncLessonsFromCourse(originalCourse.value)
    } else if (!categories.value.length) {
      courseLoadError.value = 'Chưa có danh mục khả dụng. Quản trị viên cần tạo danh mục trước khi xuất bản khóa học.'
    }
  } catch (error) {
    courseLoadError.value = providerErrorMessage(error, 'Không thể tải danh mục hoặc khóa học từ Backend.')
  }
})

async function handleCoverFile(file) {
  if (!file) return
  coverError.value = ''
  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
  if (!allowed.includes(file.type)) {
    coverError.value = 'Chỉ hỗ trợ ảnh định dạng JPG, PNG, WEBP hoặc GIF.'
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    coverError.value = 'Dung lượng ảnh không được vượt quá 5 MB.'
    return
  }
  uploadingCover.value = true
  try {
    const result = await uploadProviderCourseCover(file, courseId.value || null)
    form.coverImageUrl = result.url
    form.coverImagePath = result.rawUrl
    if (result.course) {
      originalCourse.value = { ...originalCourse.value, ...result.course }
    }
    toastMessage.value = 'Đã tải ảnh bìa khóa học lên thư mục media thành công.'
  } catch (error) {
    coverError.value = providerErrorMessage(error, 'Không thể tải ảnh bìa lên máy chủ.')
  } finally {
    uploadingCover.value = false
    if (coverInputRef.value) coverInputRef.value.value = ''
  }
}

function onCoverInputChange(event) {
  const file = event.target?.files?.[0]
  if (file) handleCoverFile(file)
}

function onCoverDrop(event) {
  isDraggingCover.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) handleCoverFile(file)
}

function removeCoverImage() {
  form.coverImageUrl = ''
  form.coverImagePath = ''
  coverError.value = ''
}

async function persistCourse() {
  const payload = {
    title: form.title.trim(),
    categoryId: form.categoryId,
    description: form.description.trim(),
    coverImagePath: form.coverImagePath || null,
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
  if (!form.title.trim() || !form.categoryId) {
    errorMessage.value = 'Vui lòng nhập tên khóa học và chọn danh mục trước khi lưu bản nháp.'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    await persistCourse()
    await persistAllLessons({ silent: true })
    toastMessage.value = 'Đã lưu bản nháp khóa học và bài học thành công.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu bản nháp.')
  } finally {
    saving.value = false
  }
}

function addLessonDraft() {
  lessonDrafts.value.push({
    id: `TEMP-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    title: '',
    durationMinutes: null,
    videoUrl: '',
    content: '',
    thuTu: lessonDrafts.value.length + 1,
    materials: [],
    dirty: true,
  })
}

function openInlineMaterialForm(lessonId) {
  if (activeMaterialLessonId.value === lessonId) {
    activeMaterialLessonId.value = ''
    return
  }
  activeMaterialLessonId.value = lessonId
  Object.assign(materialForm, {
    title: '',
    documentType: 'PDF',
    fileUrl: '',
    description: '',
  })
  selectedMaterialFile.value = null
  errorMessage.value = ''
}

async function addMaterialToLesson(lesson) {
  if (!materialForm.title.trim() || (!materialForm.fileUrl.trim() && !selectedMaterialFile.value)) {
    errorMessage.value = 'Vui lòng nhập tiêu đề và chọn tệp riêng tư hoặc URL ngoài.'
    return
  }
  savingMaterial.value = true
  errorMessage.value = ''
  try {
    if (!courseId.value) {
      await persistCourse()
    }
    let targetLessonId = lesson.id
    if (String(lesson.id).startsWith('TEMP-')) {
      if (!lesson.title.trim()) {
        errorMessage.value = 'Vui lòng nhập tên bài học trước khi đính kèm tài liệu.'
        savingMaterial.value = false
        return
      }
      const created = await createProviderLesson(
        courseId.value,
        {
          title: lesson.title.trim(),
          content: lesson.content?.trim() || '',
          durationMinutes: lesson.durationMinutes,
          video: lesson.videoUrl?.trim() ? { url: lesson.videoUrl.trim() } : null,
        },
        lesson.thuTu,
      )
      targetLessonId = String(created.maBaiHoc)
    }
    const saved = await createProviderMaterial(courseId.value, targetLessonId, {
      title: materialForm.title.trim(),
      fileUrl: materialForm.fileUrl.trim(),
      documentType: materialForm.documentType,
      description: materialForm.description.trim(),
    })
    if (selectedMaterialFile.value) {
      await uploadStandaloneMaterialFile(saved.id, selectedMaterialFile.value)
    }
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    activeMaterialLessonId.value = ''
    toastMessage.value = 'Đã đính kèm tài liệu vào bài học.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể đính kèm tài liệu vào bài học.')
  } finally {
    savingMaterial.value = false
  }
}

function selectLessonMaterialFile(event) {
  selectedMaterialFile.value = event.target.files?.[0] || null
  if (selectedMaterialFile.value) materialForm.fileUrl = ''
}

async function openAttachedMaterial(material) {
  openingMaterialId.value = String(material.id)
  errorMessage.value = ''
  try {
    await openMaterialFile({ id: material.id, fileUrl: material.fileUrl, title: material.title })
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể mở tệp tài liệu.')
  } finally {
    openingMaterialId.value = ''
  }
}

async function removeMaterialFromLesson(lessonId, materialId) {
  savingMaterial.value = true
  errorMessage.value = ''
  try {
    await deleteProviderMaterial(courseId.value, lessonId, materialId)
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    toastMessage.value = 'Đã gỡ tài liệu khỏi bài học.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể xóa tài liệu.')
  } finally {
    savingMaterial.value = false
  }
}

async function saveSingleLesson(lesson) {
  if (!lesson.title.trim()) {
    errorMessage.value = 'Vui lòng nhập tên bài học trước khi lưu.'
    return
  }
  if (!courseId.value) {
    await persistCourse()
  }
  savingLessons.value = true
  errorMessage.value = ''
  try {
    const lessonPayload = {
      title: lesson.title.trim(),
      content: lesson.content?.trim() || '',
      durationMinutes: lesson.durationMinutes,
      video: lesson.videoUrl?.trim() ? { url: lesson.videoUrl.trim() } : null,
      thuTu: lesson.thuTu,
    }
    if (String(lesson.id).startsWith('TEMP-')) {
      await createProviderLesson(courseId.value, lessonPayload, lesson.thuTu)
    } else {
      await updateProviderLesson(courseId.value, lesson.id, lessonPayload)
    }
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    toastMessage.value = 'Đã lưu bài học thành công.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu bài học.')
  } finally {
    savingLessons.value = false
  }
}

async function persistAllLessons({ silent = false } = {}) {
  if (!courseId.value || !lessonDrafts.value.length) return true
  const toSave = lessonDrafts.value.filter(
    (item) => (String(item.id).startsWith('TEMP-') || item.dirty) && item.title.trim(),
  )
  if (!toSave.length) return true

  savingLessons.value = true
  errorMessage.value = ''
  try {
    for (let i = 0; i < lessonDrafts.value.length; i += 1) {
      const lesson = lessonDrafts.value[i]
      if (!lesson.title.trim()) continue
      if (!String(lesson.id).startsWith('TEMP-') && !lesson.dirty) continue

      const lessonPayload = {
        title: lesson.title.trim(),
        content: lesson.content?.trim() || '',
        durationMinutes: lesson.durationMinutes,
        video: lesson.videoUrl?.trim() ? { url: lesson.videoUrl.trim() } : null,
        thuTu: i + 1,
      }
      if (String(lesson.id).startsWith('TEMP-')) {
        await createProviderLesson(courseId.value, lessonPayload, i + 1)
      } else {
        await updateProviderLesson(courseId.value, lesson.id, lessonPayload)
      }
    }
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    if (!silent) toastMessage.value = 'Đã lưu toàn bộ bài học.'
    return true
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu danh sách bài học.')
    return false
  } finally {
    savingLessons.value = false
  }
}

async function removeLessonDraft(lesson) {
  if (String(lesson.id).startsWith('TEMP-')) {
    lessonDrafts.value = lessonDrafts.value.filter((item) => item.id !== lesson.id)
    return
  }
  savingLessons.value = true
  errorMessage.value = ''
  try {
    await deleteProviderLesson(courseId.value, lesson.id)
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    toastMessage.value = 'Đã xóa bài học.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể xóa bài học.')
  } finally {
    savingLessons.value = false
  }
}

async function shiftLesson(lesson, direction) {
  const index = lessonDrafts.value.findIndex((item) => item.id === lesson.id)
  const other = lessonDrafts.value[index + direction]
  if (!other || String(lesson.id).startsWith('TEMP-') || String(other.id).startsWith('TEMP-')) return

  savingLessons.value = true
  errorMessage.value = ''
  try {
    const lessonOrder = lesson.thuTu || index + 1
    const otherOrder = other.thuTu || index + direction + 1
    await updateProviderLesson(courseId.value, lesson.id, {
      title: lesson.title,
      content: lesson.content,
      durationMinutes: lesson.durationMinutes,
      video: lesson.videoUrl?.trim() ? { url: lesson.videoUrl.trim() } : null,
      thuTu: otherOrder,
    })
    await updateProviderLesson(courseId.value, other.id, {
      title: other.title,
      content: other.content,
      durationMinutes: other.durationMinutes,
      video: other.videoUrl?.trim() ? { url: other.videoUrl.trim() } : null,
      thuTu: lessonOrder,
    })
    originalCourse.value = await loadProviderCourse(courseId.value)
    syncLessonsFromCourse(originalCourse.value)
    toastMessage.value = 'Đã cập nhật thứ tự bài học.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể đổi thứ tự bài học.')
  } finally {
    savingLessons.value = false
  }
}

async function goToStep(targetStep) {
  if (targetStep === step.value) return
  if (targetStep > 0 && (!form.title.trim() || !form.categoryId)) {
    errorMessage.value = 'Vui lòng nhập tên khóa học và chọn danh mục trước khi tiếp tục.'
    return
  }

  errorMessage.value = ''

  // Moving out of Step 0: auto-save draft course so courseId is ready for lessons
  if (step.value === 0 && targetStep > 0) {
    saving.value = true
    try {
      await persistCourse()
      if (!lessonDrafts.value.length && originalCourse.value?.lessons?.length) {
        syncLessonsFromCourse(originalCourse.value)
      }
      if (targetStep === 1 && !lessonDrafts.value.length) {
        addLessonDraft()
      }
    } catch (error) {
      errorMessage.value = providerErrorMessage(error, 'Không thể lưu thông tin khóa học.')
      saving.value = false
      return
    } finally {
      saving.value = false
    }
  }

  // Moving from Step 1 to Step 2: auto-save any unsaved lesson drafts
  if (step.value === 1 && targetStep === 2) {
    const ok = await persistAllLessons({ silent: true })
    if (!ok) return
  }

  step.value = targetStep
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function submitForReview() {
  submitting.value = true
  try {
    const saved = await persistCourse()
    await submitProviderCourseRecord(saved.id)
    toastMessage.value = isResubmission.value
      ? 'Đã gửi lại khóa học vào hàng đợi kiểm duyệt của Chuyên gia.'
      : 'Khóa học đã được gửi tới Chuyên gia thẩm định thành công.'
    submitConfirmOpen.value = false
    router.push({ name: 'provider-course-detail', params: { id: saved.id } })
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể gửi kiểm duyệt.')
    submitConfirmOpen.value = false
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Load Error Screen -->
    <div v-if="courseLoadError" class="bento-card p-6 bg-surface max-w-2xl">
      <UiAlert variant="danger" title="Không thể mở trình soạn khóa học" :message="courseLoadError" />
      <RouterLink :to="{ name: 'provider-courses' }" class="ui-button ui-button--outline ui-button--sm mt-4 inline-flex items-center gap-1.5">
        <ArrowLeft :size="14" aria-hidden="true" />
        <span>Quay lại danh sách khóa học</span>
      </RouterLink>
    </div>

    <!-- Non-editable Notice -->
    <div v-else-if="originalCourse && !isEditable" class="bento-card p-6 bg-surface max-w-2xl space-y-4">
      <div class="flex items-center gap-2">
        <UiStatusBadge :status="originalCourse.status" />
        <h2 class="ui-section-title">Khóa học hiện không thể chỉnh sửa</h2>
      </div>
      <p class="text-sm text-muted">
        Khóa học đang ở trạng thái <strong>{{ PROVIDER_STATUS_LABELS[originalCourse.status] }}</strong>. Khóa học đã gửi kiểm duyệt hoặc đã duyệt công khai cần tuân thủ quy trình xét duyệt của Chuyên gia.
      </p>
      <RouterLink :to="{ name: 'provider-course-detail', params: { id: courseId } }" class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5">
        <span>Xem chi tiết khóa học</span>
      </RouterLink>
    </div>

    <!-- Main 3-Step Course Editor Flow -->
    <div v-else class="space-y-6">
      <!-- Top Bar -->
      <header class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <span class="ui-tag-label">
            <GraduationCap :size="15" aria-hidden="true" />
            <span>{{ originalCourse ? 'Cập nhật khóa học' : 'Tạo mới khóa học' }}</span>
          </span>
          <h1 class="ui-page-title mt-1.5">
            {{ form.title || 'Khóa học mới chưa đặt tên' }}
          </h1>
          <p class="mt-1 text-xs sm:text-sm text-muted">
            Thiết lập thông tin chung, thêm danh sách bài học và gửi Chuyên gia kiểm duyệt.
          </p>
        </div>

        <div class="flex items-center gap-2.5">
          <button
            type="button"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
            :disabled="saving || savingLessons"
            @click="saveDraft"
          >
            <RefreshCw v-if="saving || savingLessons" :size="14" class="animate-spin" aria-hidden="true" />
            <Save v-else :size="14" aria-hidden="true" />
            <span>Lưu bản nháp</span>
          </button>
        </div>
      </header>

      <!-- Feedback Alert -->
      <UiAlert
        v-if="errorMessage"
        variant="danger"
        :message="errorMessage"
        dismissible
        @dismiss="errorMessage = ''"
      />

      <!-- 3-Step Stepper Navigation -->
      <div class="rounded-xl border border-border bg-subtle p-1.5">
        <ol class="grid grid-cols-1 gap-1.5 sm:grid-cols-3" aria-label="Các bước tạo khóa học">
          <li v-for="(label, index) in steps" :key="label">
            <button
              type="button"
              :class="[
                'flex w-full items-center justify-center gap-2 rounded-lg py-2.5 px-3 text-xs font-bold transition-colors duration-150',
                step === index
                  ? 'bg-surface text-navy shadow-xs border border-border/80'
                  : 'text-slate-600 hover:text-navy hover:bg-surface/60',
              ]"
              :disabled="saving || savingLessons || (index > 0 && (!form.title.trim() || !form.categoryId))"
              @click="goToStep(index)"
            >
              <span
                :class="[
                  'flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                  step === index ? 'bg-teal text-white' : 'bg-border text-slate-600',
                ]"
              >
                {{ index + 1 }}
              </span>
              <span class="truncate">{{ label }}</span>
            </button>
          </li>
        </ol>
      </div>

      <!-- STEP 0: THÔNG TIN KHÓA HỌC -->
      <section v-if="step === 0" class="bento-card bg-surface p-6 sm:p-8 space-y-6">
        <div class="border-b border-border pb-3">
          <h2 class="ui-section-title text-base sm:text-lg">1. Thông tin cơ bản khóa học</h2>
          <p class="text-xs text-muted mt-0.5">Các thông tin sẽ hiển thị công khai trên danh mục khóa học sau khi được duyệt.</p>
        </div>

        <div class="grid gap-5 md:grid-cols-2">
          <!-- Ảnh bìa khóa học (Upload vào media/courses) -->
          <div class="md:col-span-2">
            <label class="block text-xs font-bold text-navy mb-2">
              Ảnh bìa khóa học (tỷ lệ 16:9 khuyến nghị · JPG, PNG, WEBP tối đa 5 MB)
            </label>

            <input
              ref="coverInputRef"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              class="sr-only"
              @change="onCoverInputChange"
            >

            <div
              v-if="form.coverImageUrl"
              class="group relative overflow-hidden rounded-2xl border border-border bg-subtle"
            >
              <img
                :src="form.coverImageUrl"
                :alt="form.title || 'Ảnh bìa khóa học'"
                class="h-52 w-full object-cover sm:h-64"
              >
              <div class="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-surface px-4 py-3">
                <span class="truncate text-xs font-medium text-slate-600">
                  Ảnh đã lưu trong thư mục media · Sẽ hiển thị trên Trang chủ &amp; Danh mục khóa học
                </span>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
                    :disabled="uploadingCover"
                    @click="coverInputRef?.click()"
                  >
                    <Upload :size="13" aria-hidden="true" />
                    <span>{{ uploadingCover ? 'Đang tải...' : 'Đổi ảnh' }}</span>
                  </button>
                  <button
                    type="button"
                    class="ui-button ui-button--quiet ui-button--sm inline-flex items-center gap-1 text-danger hover:bg-danger/10"
                    :disabled="uploadingCover"
                    @click="removeCoverImage"
                  >
                    <Trash2 :size="13" aria-hidden="true" />
                    <span>Gỡ ảnh</span>
                  </button>
                </div>
              </div>
            </div>

            <div
              v-else
              role="button"
              tabindex="0"
              :class="[
                'flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-8 text-center transition-colors duration-150 cursor-pointer',
                isDraggingCover
                  ? 'border-teal bg-teal/5'
                  : 'border-border bg-subtle/40 hover:border-teal/50 hover:bg-subtle/70',
              ]"
              @click="coverInputRef?.click()"
              @keydown.enter.prevent="coverInputRef?.click()"
              @keydown.space.prevent="coverInputRef?.click()"
              @dragover.prevent="isDraggingCover = true"
              @dragleave.prevent="isDraggingCover = false"
              @drop.prevent="onCoverDrop"
            >
              <span class="flex size-12 items-center justify-center rounded-xl bg-teal/10 text-teal">
                <RefreshCw v-if="uploadingCover" :size="22" class="animate-spin" aria-hidden="true" />
                <ImagePlus v-else :size="22" aria-hidden="true" />
              </span>
              <div class="space-y-1">
                <p class="text-sm font-semibold text-navy">
                  {{ uploadingCover ? 'Đang tải ảnh lên máy chủ...' : 'Nhấn để chọn ảnh hoặc kéo thả ảnh bìa vào đây' }}
                </p>
                <p class="text-xs text-slate-600">
                  Hỗ trợ JPG, PNG, WEBP, GIF · Tối đa 5 MB · Lưu trực tiếp vào thư mục <code class="font-mono text-navy">media/courses</code>
                </p>
              </div>
            </div>

            <p v-if="coverError" class="mt-2 text-xs font-medium text-danger" role="alert">
              {{ coverError }}
            </p>
          </div>

          <!-- Tên khóa học -->
          <div class="md:col-span-2">
            <label class="block text-xs font-bold text-navy mb-1.5">
              Tên khóa học <span class="text-danger">*</span>
            </label>
            <input
              v-model="form.title"
              maxlength="255"
              class="ui-input"
              placeholder="VD: Lập trình Vue 3 toàn diện từ cơ bản đến nâng cao"
              required
            >
          </div>

          <!-- Danh mục -->
          <div>
            <label class="block text-xs font-bold text-navy mb-1.5">
              Danh mục đào tạo <span class="text-danger">*</span>
            </label>
            <select v-model="form.categoryId" class="ui-input bg-surface" required>
              <option value="">-- Chọn danh mục phù hợp --</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
          </div>

          <!-- Trình độ -->
          <div>
            <label class="block text-xs font-bold text-navy mb-1.5">
              Trình độ yêu cầu
            </label>
            <input
              v-model="form.level"
              maxlength="100"
              class="ui-input"
              placeholder="VD: Cơ bản, Trung cấp, Nâng cao..."
            >
          </div>

          <!-- Thời lượng (phút) -->
          <div>
            <label class="block text-xs font-bold text-navy mb-1.5">
              Tổng thời lượng dự kiến (phút)
            </label>
            <input
              v-model.number="form.durationMinutes"
              type="number"
              min="0"
              class="ui-input"
              placeholder="VD: 360"
            >
          </div>

          <!-- Học phí -->
          <div>
            <label class="block text-xs font-bold text-navy mb-1.5">
              Học phí (VND)
            </label>
            <input
              v-model.number="form.price"
              type="number"
              min="0"
              step="1000"
              class="ui-input"
              placeholder="Để trống nếu chưa xác định, 0 là Miễn phí"
            >
          </div>

          <!-- Mô tả -->
          <div class="md:col-span-2">
            <label class="block text-xs font-bold text-navy mb-1.5">
              Mô tả chi tiết khóa học
            </label>
            <textarea
              v-model="form.description"
              rows="5"
              class="ui-input min-h-28"
              placeholder="Tóm tắt mục tiêu, kiến thức người học sẽ đạt được và yêu cầu tiên quyết..."
            />
          </div>
        </div>

        <!-- Stepper Bottom Controls -->
        <div class="flex items-center justify-between pt-4 border-t border-border">
          <RouterLink
            :to="{ name: 'provider-courses' }"
            class="ui-button ui-button--quiet ui-button--sm inline-flex items-center gap-1.5"
          >
            <ArrowLeft :size="15" aria-hidden="true" />
            <span>Hủy &amp; Quay lại</span>
          </RouterLink>

          <UiButton
            type="button"
            variant="primary"
            :disabled="saving"
            @click="goToStep(1)"
          >
            <span>{{ saving ? 'Đang lưu…' : 'Tiếp tục: Thêm bài học' }}</span>
            <ArrowRight :size="15" aria-hidden="true" />
          </UiButton>
        </div>
      </section>

      <!-- STEP 1: SOẠN BÀI HỌC & TÀI LIỆU ĐÍNH KÈM TRỰC TIẾP -->
      <section v-else-if="step === 1" class="bento-card bg-surface p-6 sm:p-8 space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <h2 class="ui-section-title text-base sm:text-lg">
              2. Bài học &amp; Tài liệu đi kèm ({{ lessonDrafts.length }} bài học)
            </h2>
            <p class="mt-0.5 text-xs text-muted">
              Thêm bài học, đường dẫn video và đính kèm tài liệu học tập trực tiếp cho từng bài.
            </p>
          </div>

          <button
            type="button"
            class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
            :disabled="savingLessons || savingMaterial"
            @click="addLessonDraft"
          >
            <Plus :size="15" aria-hidden="true" />
            <span>Thêm bài học</span>
          </button>
        </div>

        <div v-if="lessonDrafts.length" class="space-y-4">
          <article
            v-for="(lesson, index) in lessonDrafts"
            :key="lesson.id"
            class="rounded-xl border border-border bg-background/60 p-4 sm:p-5 space-y-4"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2.5">
                <span class="flex size-6 items-center justify-center rounded-md bg-navy text-xs font-bold text-white">
                  {{ index + 1 }}
                </span>
                <p class="text-sm font-bold text-navy">
                  {{ lesson.title.trim() || `Bài học ${index + 1}` }}
                </p>
                <span
                  v-if="String(lesson.id).startsWith('TEMP-')"
                  class="rounded-full bg-amber/15 px-2 py-0.5 text-[11px] font-semibold text-amber"
                >
                  Chưa lưu
                </span>
                <span
                  v-else-if="lesson.dirty"
                  class="rounded-full bg-teal/15 px-2 py-0.5 text-[11px] font-semibold text-teal-dark"
                >
                  Có thay đổi
                </span>
              </div>

              <div class="flex items-center gap-1">
                <button
                  type="button"
                  class="rounded-lg border border-border bg-surface p-1.5 text-slate-600 transition-colors hover:text-navy disabled:opacity-40"
                  :disabled="savingLessons || index === 0 || String(lesson.id).startsWith('TEMP-')"
                  aria-label="Chuyển bài học lên"
                  @click="shiftLesson(lesson, -1)"
                >
                  <ArrowUp :size="14" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-border bg-surface p-1.5 text-slate-600 transition-colors hover:text-navy disabled:opacity-40"
                  :disabled="savingLessons || index === lessonDrafts.length - 1 || String(lesson.id).startsWith('TEMP-')"
                  aria-label="Chuyển bài học xuống"
                  @click="shiftLesson(lesson, 1)"
                >
                  <ArrowDown :size="14" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-teal-dark transition-colors hover:border-teal/50 hover:bg-teal/5 disabled:opacity-40"
                  :disabled="savingLessons"
                  @click="saveSingleLesson(lesson)"
                >
                  <Save :size="13" aria-hidden="true" />
                  <span>Lưu</span>
                </button>
                <button
                  type="button"
                  class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-danger/10 hover:text-danger disabled:opacity-40"
                  :disabled="savingLessons"
                  aria-label="Xóa bài học"
                  @click="removeLessonDraft(lesson)"
                >
                  <Trash2 :size="14" aria-hidden="true" />
                </button>
              </div>
            </div>

            <div class="grid gap-3 md:grid-cols-2">
              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">
                  Tên bài học <span class="text-danger">*</span>
                </label>
                <input
                  v-model="lesson.title"
                  type="text"
                  placeholder="VD: Bài 1 - Giới thiệu tổng quan & cài đặt môi trường"
                  class="ui-input bg-surface"
                  @input="lesson.dirty = true"
                >
              </div>

              <div>
                <label class="mb-1 block text-xs font-semibold text-navy">Thời lượng (phút)</label>
                <input
                  v-model.number="lesson.durationMinutes"
                  type="number"
                  min="0"
                  placeholder="VD: 25"
                  class="ui-input bg-surface"
                  @input="lesson.dirty = true"
                >
              </div>

              <div class="md:col-span-2">
                <label class="mb-1 block text-xs font-semibold text-navy">Đường dẫn video bài giảng (tùy chọn)</label>
                <input
                  v-model="lesson.videoUrl"
                  type="text"
                  placeholder="https://... (YouTube, Vimeo hoặc link video bài giảng)"
                  class="ui-input bg-surface"
                  @input="lesson.dirty = true"
                >
              </div>

              <div class="md:col-span-2">
                <label class="mb-1 block text-xs font-semibold text-navy">Nội dung bài học</label>
                <textarea
                  v-model="lesson.content"
                  rows="3"
                  placeholder="Tóm tắt kiến thức chính, mục tiêu hoặc bài tập thực hành của bài học..."
                  class="ui-input bg-surface"
                  @input="lesson.dirty = true"
                />
              </div>
            </div>

            <!-- Inline Attached Materials for this Lesson -->
            <div class="border-t border-border/70 pt-3.5 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="inline-flex items-center gap-1.5 text-xs font-semibold text-navy">
                  <Paperclip :size="13" class="text-teal" aria-hidden="true" />
                  <span>Tài liệu đi kèm bài học ({{ lesson.materials?.length || 0 }})</span>
                </span>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-semibold text-teal-dark transition-colors hover:border-teal/50 hover:bg-teal/5"
                  :disabled="savingMaterial"
                  @click="openInlineMaterialForm(lesson.id)"
                >
                  <Plus :size="13" aria-hidden="true" />
                  <span>{{ activeMaterialLessonId === lesson.id ? 'Đóng form tài liệu' : 'Đính kèm tài liệu' }}</span>
                </button>
              </div>

              <!-- Existing attached materials -->
              <ul v-if="lesson.materials?.length" class="space-y-1.5">
                <li
                  v-for="mat in lesson.materials"
                  :key="mat.id"
                  class="flex items-center justify-between gap-3 rounded-lg border border-border/80 bg-surface px-3 py-2 text-xs"
                >
                  <div class="flex min-w-0 items-center gap-2">
                    <FileText :size="14" class="shrink-0 text-teal" aria-hidden="true" />
                    <span class="rounded bg-subtle px-1.5 py-0.5 text-[10px] font-bold uppercase text-navy">
                      {{ mat.documentType || 'DOCUMENT' }}
                    </span>
                    <span class="truncate font-semibold text-navy">{{ mat.title }}</span>
                  </div>
                  <div class="flex shrink-0 items-center gap-1.5">
                    <button
                      v-if="mat.fileUrl"
                      type="button"
                      class="rounded p-1 text-slate-400 transition-colors hover:text-navy"
                      aria-label="Mở liên kết tài liệu"
                      @click="openAttachedMaterial(mat)"
                    >
                      <ExternalLink :size="13" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-slate-400 transition-colors hover:bg-danger/10 hover:text-danger"
                      :disabled="savingMaterial"
                      aria-label="Gỡ tài liệu"
                      @click="removeMaterialFromLesson(lesson.id, mat.id)"
                    >
                      <Trash2 :size="13" aria-hidden="true" />
                    </button>
                  </div>
                </li>
              </ul>

              <!-- Inline Add Material Form -->
              <div
                v-if="activeMaterialLessonId === lesson.id"
                class="rounded-xl border border-teal/25 bg-surface p-3.5 space-y-3"
              >
                <div class="grid gap-3 sm:grid-cols-3">
                  <div class="sm:col-span-2">
                    <label class="mb-1 block text-[11px] font-semibold text-navy">
                      Tiêu đề tài liệu <span class="text-danger">*</span>
                    </label>
                    <input
                      v-model="materialForm.title"
                      type="text"
                      placeholder="VD: Slide bài giảng Chương 1 (PDF)"
                      class="ui-input"
                    >
                  </div>
                  <div>
                    <label class="mb-1 block text-[11px] font-semibold text-navy">Định dạng</label>
                    <select v-model="materialForm.documentType" class="ui-input">
                      <option value="PDF">PDF</option>
                      <option value="SLIDE">SLIDE</option>
                      <option value="DOCUMENT">DOCUMENT</option>
                      <option value="CODE">CODE</option>
                      <option value="EXERCISE">EXERCISE</option>
                      <option value="REFERENCE">REFERENCE</option>
                    </select>
                  </div>
                </div>

                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label class="mb-1 block text-[11px] font-semibold text-navy">Tệp riêng tư</label>
                    <input
                      type="file"
                      accept=".pdf,.txt,.csv,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.webp"
                      class="block w-full text-xs text-ink file:mr-2 file:rounded-lg file:border-0 file:bg-teal file:px-2.5 file:py-2 file:font-semibold file:text-white"
                      @change="selectLessonMaterialFile"
                    >
                  </div>
                  <div>
                  <label class="mb-1 block text-[11px] font-semibold text-navy">
                    Hoặc URL tài liệu ngoài
                  </label>
                  <input
                    v-model="materialForm.fileUrl"
                    type="url"
                    :disabled="Boolean(selectedMaterialFile)"
                    placeholder="https://example.org/material.pdf"
                    class="ui-input"
                  >
                  </div>
                </div>

                <div>
                  <label class="mb-1 block text-[11px] font-semibold text-navy">Mô tả ngắn (tùy chọn)</label>
                  <input
                    v-model="materialForm.description"
                    type="text"
                    placeholder="Ghi chú ngắn cho người học..."
                    class="ui-input"
                  >
                </div>

                <div class="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    class="ui-button ui-button--outline ui-button--sm"
                    :disabled="savingMaterial"
                    @click="activeMaterialLessonId = ''"
                  >
                    Hủy
                  </button>
                  <button
                    type="button"
                    class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
                    :disabled="savingMaterial"
                    @click="addMaterialToLesson(lesson)"
                  >
                    <Save :size="13" aria-hidden="true" />
                    <span>{{ savingMaterial ? 'Đang lưu…' : 'Lưu tài liệu' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-dashed border-border bg-subtle/40 p-8 text-center space-y-3"
        >
          <p class="text-sm font-semibold text-navy">Khóa học chưa có bài học nào</p>
          <p class="text-xs text-slate-600">Thêm bài học đầu tiên để hoàn thiện cấu trúc khóa học.</p>
          <button
            type="button"
            class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5"
            @click="addLessonDraft"
          >
            <Plus :size="14" aria-hidden="true" />
            <span>Thêm bài học đầu tiên</span>
          </button>
        </div>

        <!-- Stepper Bottom Controls -->
        <div class="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-border">
          <button
            type="button"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
            @click="goToStep(0)"
          >
            <ArrowLeft :size="15" aria-hidden="true" />
            <span>Quay lại thông tin</span>
          </button>

          <UiButton
            type="button"
            variant="primary"
            :disabled="savingLessons"
            @click="goToStep(2)"
          >
            <span>{{ savingLessons ? 'Đang lưu bài học…' : 'Tiếp tục: Xem trước & Gửi duyệt' }}</span>
            <ArrowRight :size="15" aria-hidden="true" />
          </UiButton>
        </div>
      </section>

      <!-- STEP 2: XEM TRƯỚC & GỬI KIỂM DUYỆT -->
      <section v-else class="space-y-6">
        <div class="grid gap-6 lg:grid-cols-[1fr_340px] items-start">
          <!-- Left: Live Course Preview -->
          <div class="space-y-4">
            <div class="bento-card bg-surface p-6 space-y-4">
              <div class="flex items-center justify-between border-b border-border pb-3">
                <span class="text-xs font-bold uppercase tracking-wider text-teal">
                  Bản xem trước khóa học
                </span>
                <UiStatusBadge status="Draft" label="Xem trước bản nháp" />
              </div>

              <div v-if="form.coverImageUrl" class="overflow-hidden rounded-xl border border-border bg-subtle">
                <img
                  :src="form.coverImageUrl"
                  :alt="form.title || 'Ảnh bìa khóa học'"
                  class="h-48 w-full object-cover sm:h-56"
                >
              </div>

              <div>
                <span class="rounded bg-navy px-2.5 py-0.5 text-xs font-bold text-white">
                  {{ selectedCategoryName }}
                </span>
                <h3 class="mt-2 text-xl sm:text-2xl font-bold text-navy">
                  {{ form.title || 'Chưa đặt tên khóa học' }}
                </h3>
                <p class="mt-2 whitespace-pre-line text-xs sm:text-sm text-muted leading-relaxed">
                  {{ form.description || 'Chưa có mô tả khóa học.' }}
                </p>
              </div>

              <!-- Quick specs -->
              <div class="grid grid-cols-3 gap-3 border-t border-border/80 pt-3 text-xs">
                <div>
                  <span class="text-muted block text-[10px] uppercase font-semibold">Trình độ</span>
                  <span class="font-bold text-navy">{{ form.level || 'Linh hoạt' }}</span>
                </div>
                <div>
                  <span class="text-muted block text-[10px] uppercase font-semibold">Thời lượng</span>
                  <span class="font-bold text-navy">{{ form.durationMinutes ? `${form.durationMinutes} phút` : 'Chưa có' }}</span>
                </div>
                <div>
                  <span class="text-muted block text-[10px] uppercase font-semibold">Học phí</span>
                  <span class="font-bold text-navy">{{ form.price != null ? (form.price === 0 ? 'Miễn phí' : `${form.price.toLocaleString('vi-VN')} ₫`) : 'Chưa xác định' }}</span>
                </div>
              </div>

              <!-- Lessons summary -->
              <div class="border-t border-border/80 pt-3">
                <div class="flex items-center justify-between text-xs mb-2">
                  <span class="font-bold text-navy">Danh sách bài học ({{ savedLessonsCount }})</span>
                  <button
                    type="button"
                    class="text-teal font-semibold hover:underline"
                    @click="goToStep(1)"
                  >
                    Chỉnh sửa bài học →
                  </button>
                </div>

                <ul v-if="originalCourse?.lessons?.length" class="space-y-1.5 text-xs">
                  <li
                    v-for="(lesson, idx) in originalCourse.lessons"
                    :key="lesson.id"
                    class="flex items-center justify-between gap-2 rounded bg-subtle p-2 text-ink"
                  >
                    <div class="flex min-w-0 items-center gap-2">
                      <span class="size-5 flex items-center justify-center rounded-full bg-border text-[10px] font-bold shrink-0">
                        {{ idx + 1 }}
                      </span>
                      <span class="truncate font-medium">{{ lesson.title }}</span>
                    </div>
                    <span class="shrink-0 text-[11px] text-slate-500">
                      <template v-if="lesson.durationMinutes">{{ lesson.durationMinutes }} phút</template>
                      <template v-if="lesson.materials?.length">
                        {{ lesson.durationMinutes ? ' · ' : '' }}{{ lesson.materials.length }} tài liệu
                      </template>
                    </span>
                  </li>
                </ul>

                <div v-else class="flex flex-wrap items-center justify-between gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                  <span>Khóa học chưa có bài học nào được lưu.</span>
                  <button
                    type="button"
                    class="font-semibold text-navy underline"
                    @click="goToStep(1)"
                  >
                    Thêm bài học ngay →
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: Submission Criteria Checklist -->
          <aside class="space-y-4">
            <div class="bento-card bg-surface p-5 space-y-4">
              <h3 class="text-xs font-bold uppercase tracking-wider text-navy">
                Tiêu chuẩn kiểm duyệt học thuật
              </h3>

              <ul class="space-y-2.5 text-xs">
                <li class="flex items-start gap-2" :class="form.title.trim() ? 'text-success' : 'text-muted'">
                  <CheckCircle2 :size="15" class="shrink-0 mt-0.5" aria-hidden="true" />
                  <span>Tên khóa học rõ ràng, súc tích</span>
                </li>

                <li class="flex items-start gap-2" :class="form.categoryId ? 'text-success' : 'text-muted'">
                  <CheckCircle2 :size="15" class="shrink-0 mt-0.5" aria-hidden="true" />
                  <span>Đã phân loại đúng danh mục chuyên môn</span>
                </li>

                <li class="flex items-start gap-2" :class="savedLessonsCount > 0 ? 'text-success' : 'text-muted'">
                  <CheckCircle2 :size="15" class="shrink-0 mt-0.5" aria-hidden="true" />
                  <span>Có ít nhất 1 bài học hợp lệ đã lưu ({{ savedLessonsCount }})</span>
                </li>
              </ul>

              <div class="border-t border-border pt-3">
                <p class="text-[11px] text-muted leading-relaxed">
                  Khi bấm gửi duyệt, khóa học sẽ được chuyển tới hàng đợi của Chuyên gia độc lập. Sau khi được duyệt, khóa học sẽ xuất hiện công khai cho người học.
                </p>
              </div>

              <!-- Submit Button -->
              <UiButton
                type="button"
                variant="primary"
                class="w-full inline-flex items-center justify-center gap-2"
                :disabled="validationIssues.length > 0 || submitting"
                @click="submitConfirmOpen = true"
              >
                <Send :size="15" aria-hidden="true" />
                <span>{{ isResubmission ? 'Gửi lại kiểm duyệt' : 'Gửi kiểm duyệt ngay' }}</span>
              </UiButton>

              <div v-if="validationIssues.length > 0" class="space-y-1 text-[11px] text-danger">
                <p v-for="err in validationIssues" :key="err">• {{ err }}</p>
              </div>
            </div>
          </aside>
        </div>

        <!-- Stepper Bottom Controls -->
        <div class="flex items-center justify-between pt-4 border-t border-border">
          <button
            type="button"
            class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
            @click="goToStep(1)"
          >
            <ArrowLeft :size="15" aria-hidden="true" />
            <span>Quay lại soạn bài học</span>
          </button>
        </div>
      </section>

      <!-- Confirmation Modal -->
      <AdminModal
        :open="submitConfirmOpen"
        mode="confirm"
        :title="isResubmission ? 'Xác nhận gửi lại thẩm định' : 'Xác nhận gửi kiểm duyệt khóa học'"
        :description="form.title || 'Khóa học chưa đặt tên'"
        confirm-label="Gửi kiểm duyệt"
        @close="submitConfirmOpen = false"
        @confirm="submitForReview"
      >
        <p class="text-xs sm:text-sm text-muted leading-relaxed">
          Khóa học sẽ được chuyển trạng thái sang <strong>Chờ kiểm duyệt</strong> và chuyển tới Hội đồng Chuyên gia. Bạn sẽ nhận được phản hồi sau khi thẩm định hoàn tất.
        </p>
      </AdminModal>

      <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
    </div>
  </div>
</template>
