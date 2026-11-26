<script setup>
import { computed, ref, watch } from 'vue'
import {
  ArrowLeft,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  ListOrdered,
  Maximize2,
  Minimize2,
  PanelRightClose,
  PanelRightOpen,
  PlayCircle,
  RefreshCw,
  Sparkles,
  Video,
  X,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import MaterialCard from '@/components/user/MaterialCard.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  completeLearningLesson,
  fetchLearningCourse,
  fetchLearningProgress,
  fetchRecommendedMaterialsWithMeta,
} from '@/service/userApiService'
import { openMaterialFile } from '@/service/materialFileService'

const route = useRoute()
const course = ref(null)
const progress = ref(null)
const loading = ref(false)
const error = ref('')
const actionError = ref('')
const savingLesson = ref(null)
const openingMaterialId = ref('')

const activeLessonIndex = ref(0)
const activeTab = ref('content') // 'content' | 'materials'
const sidebarOpen = ref(true)
const theaterMode = ref(false)
const mobileDrawerOpen = ref(false)

const lessonMaterials = ref([])
const lessonMaterialsLoading = ref(false)
const lessonMaterialsError = ref('')
const lessonMaterialsForbidden = ref(false)

let sequence = 0
let materialsSequence = 0

const activeLesson = computed(() => {
  if (!course.value?.lessons?.length) return null
  return course.value.lessons[activeLessonIndex.value] || course.value.lessons[0]
})

const hasNextLesson = computed(() => {
  if (!course.value?.lessons?.length) return false
  return activeLessonIndex.value < course.value.lessons.length - 1
})

const hasPrevLesson = computed(() => activeLessonIndex.value > 0)

const showDesktopSidebar = computed(() => sidebarOpen.value && !theaterMode.value)

const directLessonMaterials = computed(() => activeLesson.value?.materials || [])

// Strict allowlist for safe external video URLs and YouTube privacy-enhanced embeds (anti-XSS)
const safeVideoUrl = computed(() => {
  const raw = String(activeLesson.value?.videoUrl || '').trim()
  if (!/^https?:\/\//i.test(raw)) return ''
  return raw
})

const safeYoutubeEmbedUrl = computed(() => {
  const raw = safeVideoUrl.value
  if (!raw) return ''
  try {
    const u = new URL(raw)
    const host = u.hostname.replace(/^www\./i, '').toLowerCase()
    let videoId = ''
    if (host === 'youtu.be') {
      videoId = u.pathname.replace(/^\//, '').split('/')[0]
    } else if (host === 'youtube.com' || host === 'm.youtube.com' || host === 'youtube-nocookie.com') {
      if (u.pathname === '/watch') {
        videoId = u.searchParams.get('v') || ''
      } else if (u.pathname.startsWith('/embed/')) {
        videoId = u.pathname.split('/embed/')[1]?.split('/')[0] || ''
      }
    }
    if (/^[A-Za-z0-9_-]{11}$/.test(videoId)) {
      return `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`
    }
  } catch {
    return ''
  }
  return ''
})

const totalMaterialBadgeCount = computed(() => {
  const directIds = new Set(directLessonMaterials.value.map((m) => String(m.id)))
  const extraCount = lessonMaterials.value.filter((m) => !directIds.has(String(m.id))).length
  return directIds.size + extraCount
})

function toggleTheaterMode() {
  theaterMode.value = !theaterMode.value
  if (!theaterMode.value) {
    sidebarOpen.value = true
  }
}

function toggleDesktopSidebar() {
  if (theaterMode.value) {
    theaterMode.value = false
    sidebarOpen.value = true
    return
  }
  sidebarOpen.value = !sidebarOpen.value
}

async function openLessonMaterial(material) {
  openingMaterialId.value = String(material.id)
  actionError.value = ''
  try {
    await openMaterialFile({ id: material.id, fileUrl: material.url, title: material.title })
  } catch (cause) {
    actionError.value = cause.response?.data?.detail || 'Không thể mở tệp tài liệu. Vui lòng kiểm tra lại quyền đăng ký khóa học.'
  } finally {
    openingMaterialId.value = ''
  }
}

async function loadLessonRecommendedMaterials(courseId, lessonId) {
  const reqId = ++materialsSequence
  lessonMaterialsLoading.value = true
  lessonMaterialsError.value = ''
  lessonMaterialsForbidden.value = false
  lessonMaterials.value = []

  if (!courseId || !lessonId) {
    lessonMaterialsLoading.value = false
    return
  }

  try {
    const result = await fetchRecommendedMaterialsWithMeta(courseId, {
      lessonId,
      limit: 6,
    })
    if (reqId !== materialsSequence) return
    lessonMaterials.value = result.items || []
  } catch (cause) {
    if (reqId !== materialsSequence) return
    if (cause.response?.status === 403) {
      lessonMaterialsForbidden.value = true
      lessonMaterialsError.value = cause.response?.data?.detail || 'Bạn không có quyền truy cập tài liệu gợi ý của khóa học này.'
    } else {
      lessonMaterialsError.value = cause.response?.data?.detail || 'Không thể tải tài liệu gợi ý cho bài học.'
    }
  } finally {
    if (reqId === materialsSequence) {
      lessonMaterialsLoading.value = false
    }
  }
}

async function loadCourse(courseId) {
  const current = ++sequence
  loading.value = true
  error.value = ''
  actionError.value = ''
  course.value = null
  savingLesson.value = null
  activeLessonIndex.value = 0
  activeTab.value = 'content'

  try {
    const [learning, currentProgress] = await Promise.all([
      fetchLearningCourse(courseId),
      fetchLearningProgress(courseId),
    ])
    if (current !== sequence) return
    course.value = learning
    progress.value = currentProgress

    if (learning.lessons?.length) {
      const firstIncompleteIdx = learning.lessons.findIndex((l) => !l.completed)
      if (firstIncompleteIdx >= 0) {
        activeLessonIndex.value = firstIncompleteIdx
      }
    }
  } catch (cause) {
    if (current === sequence) {
      error.value = cause.response?.data?.detail || 'Không thể tải nội dung học tập. Hãy thử lại.'
    }
  } finally {
    if (current === sequence) {
      loading.value = false
    }
  }
}

async function completeLesson(lesson) {
  if (!lesson || lesson.completed || savingLesson.value) return
  const current = sequence
  const courseId = String(route.params.courseId)
  savingLesson.value = lesson.id
  actionError.value = ''

  try {
    const updatedProgress = await completeLearningLesson(courseId, lesson.id)
    if (current !== sequence) return
    progress.value = updatedProgress
    lesson.completed = true

    if (hasNextLesson.value) {
      activeLessonIndex.value++
    }
  } catch (cause) {
    if (current === sequence) {
      actionError.value = cause.response?.data?.detail || 'Không thể lưu tiến độ bài học. Vui lòng thử lại.'
    }
  } finally {
    if (current === sequence) {
      savingLesson.value = null
    }
  }
}

function selectLesson(index) {
  activeLessonIndex.value = index
  mobileDrawerOpen.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goToNext() {
  if (hasNextLesson.value) {
    selectLesson(activeLessonIndex.value + 1)
  }
}

function goToPrev() {
  if (hasPrevLesson.value) {
    selectLesson(activeLessonIndex.value - 1)
  }
}

watch(() => route.params.courseId, loadCourse, { immediate: true })

watch(
  () => [route.params.courseId, activeLesson.value?.id],
  ([courseId, lessonId]) => {
    if (courseId && lessonId) {
      loadLessonRecommendedMaterials(courseId, lessonId)
    } else {
      lessonMaterials.value = []
      lessonMaterialsError.value = ''
      lessonMaterialsForbidden.value = false
    }
  },
)
</script>

<template>
  <div class="space-y-6">
    <!-- Compact Learning Header -->
    <header class="flex flex-col gap-4 border-b border-border pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex min-w-0 items-center gap-3">
        <RouterLink
          :to="{ name: 'learning-progress' }"
          class="inline-flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface text-muted transition-colors hover:border-navy hover:text-navy"
          aria-label="Quay lại khóa học của tôi"
        >
          <ArrowLeft :size="16" aria-hidden="true" />
        </RouterLink>

        <div class="min-w-0">
          <span class="block text-[11px] font-semibold uppercase tracking-wider text-teal">
            Phòng học tập trung
          </span>
          <h1 class="line-clamp-1 text-base font-bold text-navy sm:text-lg">
            {{ course?.course?.title || 'Đang tải khóa học…' }}
          </h1>
        </div>
      </div>

      <!-- Progress + View Controls -->
      <div class="flex flex-wrap items-center gap-2.5">
        <div v-if="progress" class="flex items-center gap-3 text-xs">
          <div class="hidden w-32 sm:block">
            <div class="mb-1 flex justify-between text-[11px] font-semibold text-muted">
              <span>Tiến độ</span>
              <span class="font-bold text-navy tabular-nums">{{ progress.percentage || 0 }}%</span>
            </div>
            <div class="h-1.5 w-full overflow-hidden rounded-full bg-border">
              <div
                class="h-full bg-teal transition-all duration-300"
                :style="{ width: `${progress.percentage || 0}%` }"
              />
            </div>
          </div>
          <span class="rounded-md bg-teal/10 px-2.5 py-1 font-bold text-teal-dark tabular-nums">
            {{ progress.completedLessons || 0 }}/{{ progress.totalLessons || 0 }} bài
          </span>
        </div>

        <!-- Desktop Sidebar Collapse Toggle -->
        <button
          v-if="course"
          type="button"
          class="hidden lg:inline-flex ui-button ui-button--outline ui-button--sm items-center gap-1.5"
          :title="showDesktopSidebar ? 'Thu gọn danh sách bài học' : 'Mở danh sách bài học'"
          @click="toggleDesktopSidebar"
        >
          <PanelRightClose v-if="showDesktopSidebar" :size="15" aria-hidden="true" />
          <PanelRightOpen v-else :size="15" aria-hidden="true" />
          <span>{{ showDesktopSidebar ? 'Thu gọn đề cương' : 'Mở đề cương' }}</span>
        </button>

        <!-- Desktop Theater Mode Toggle -->
        <button
          v-if="course"
          type="button"
          :class="[
            'hidden lg:inline-flex ui-button ui-button--sm items-center gap-1.5',
            theaterMode ? 'ui-button--primary' : 'ui-button--outline',
          ]"
          :aria-pressed="theaterMode"
          @click="toggleTheaterMode"
        >
          <Minimize2 v-if="theaterMode" :size="14" aria-hidden="true" />
          <Maximize2 v-else :size="14" aria-hidden="true" />
          <span>{{ theaterMode ? 'Thoát tập trung' : 'Theater Mode' }}</span>
        </button>

        <!-- Mobile Syllabus Drawer Toggle -->
        <button
          v-if="course"
          type="button"
          class="lg:hidden ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          @click="mobileDrawerOpen = !mobileDrawerOpen"
        >
          <ListOrdered :size="15" aria-hidden="true" />
          <span>Danh sách bài</span>
        </button>
      </div>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div class="space-y-4">
        <UiSkeleton variant="image" height="260px" />
        <UiSkeleton variant="text" :lines="6" />
      </div>
      <div>
        <UiSkeleton variant="table" :lines="5" />
      </div>
    </div>

    <!-- Error State (including 403) -->
    <UiAlert
      v-else-if="error"
      variant="danger"
      title="Không thể mở phòng học"
      :message="error"
      class="max-w-2xl"
    >
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
          @click="loadCourse(route.params.courseId)"
        >
          <RefreshCw :size="14" aria-hidden="true" />
          <span>Thử lại</span>
        </button>
        <RouterLink
          :to="{ name: 'course-detail', params: { id: route.params.courseId } }"
          class="ui-button ui-button--primary ui-button--sm"
        >
          Xem chi tiết khóa học
        </RouterLink>
      </div>
    </UiAlert>

    <!-- Main Learning Room -->
    <div
      v-else-if="course"
      :class="[
        'grid gap-6 items-start transition-all',
        showDesktopSidebar ? 'lg:grid-cols-[minmax(0,1fr)_320px]' : 'grid-cols-1',
      ]"
    >
      <!-- CENTER LEARNING CONTENT -->
      <main :class="['min-w-0 space-y-6', theaterMode ? 'mx-auto w-full max-w-5xl' : '']">
        <UiAlert
          v-if="actionError"
          variant="danger"
          :message="actionError"
          dismissible
          @dismiss="actionError = ''"
        />

        <div v-if="activeLesson" class="bento-card space-y-6 bg-surface p-5 sm:p-8">
          <!-- Active Lesson Header -->
          <div class="border-b border-border pb-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="inline-flex items-center gap-1.5 text-xs font-semibold text-teal">
                <PlayCircle :size="14" aria-hidden="true" />
                <span>Bài học {{ activeLessonIndex + 1 }} / {{ course.lessons.length }}</span>
              </span>

              <span
                v-if="activeLesson.completed"
                class="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-success"
              >
                <Check :size="12" aria-hidden="true" />
                <span>Đã hoàn thành</span>
              </span>
            </div>

            <h2 class="mt-2 text-xl font-bold text-navy sm:text-2xl">
              {{ activeLesson.title }}
            </h2>
          </div>

          <!-- Safe Video Player (Allowlisted YouTube privacy-enhanced embed or safe external link) -->
          <div v-if="safeVideoUrl" class="space-y-2.5">
            <div
              v-if="safeYoutubeEmbedUrl"
              class="overflow-hidden rounded-xl border border-border bg-navy aspect-video"
            >
              <iframe
                :src="safeYoutubeEmbedUrl"
                :title="activeLesson.title"
                class="h-full w-full"
                loading="lazy"
                referrerpolicy="strict-origin-when-cross-origin"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
              />
            </div>

            <div
              v-else
              class="overflow-hidden rounded-xl border border-border bg-navy p-6 text-center text-white sm:p-8"
            >
              <Video :size="44" class="mx-auto mb-3 text-teal" aria-hidden="true" />
              <h3 class="mb-2 text-base font-bold text-white">Video bài giảng trực tuyến</h3>
              <p class="mx-auto mb-4 max-w-md text-xs text-slate-300">
                Mở liên kết nguồn bên dưới để xem video bài giảng trực tiếp tại trang phát hành.
              </p>
              <a
                :href="safeVideoUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="ui-button ui-button--secondary inline-flex items-center gap-2"
              >
                <span>Mở bài giảng video tại nguồn</span>
                <ExternalLink :size="14" aria-hidden="true" />
              </a>
            </div>

            <div v-if="safeYoutubeEmbedUrl" class="flex items-center justify-between gap-2 text-xs text-muted">
              <span>Nguồn video phát trực tiếp từ YouTube (không lưu trữ lại trên hệ thống).</span>
              <a
                :href="safeVideoUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex shrink-0 items-center gap-1 font-semibold text-teal hover:underline"
              >
                <span>Mở tại nguồn</span>
                <ExternalLink :size="12" aria-hidden="true" />
              </a>
            </div>
          </div>

          <!-- Lesson Sub-Tabs: Content vs Learning Materials -->
          <div class="border-b border-border" role="tablist" aria-label="Nội dung và tài liệu bài học">
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                role="tab"
                :aria-selected="activeTab === 'content'"
                :class="[
                  'inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors',
                  activeTab === 'content'
                    ? 'border-teal text-navy'
                    : 'border-transparent text-muted hover:text-navy',
                ]"
                @click="activeTab = 'content'"
              >
                <BookOpen :size="15" aria-hidden="true" />
                <span>Nội dung bài học</span>
              </button>

              <button
                type="button"
                role="tab"
                :aria-selected="activeTab === 'materials'"
                :class="[
                  'inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-semibold transition-colors',
                  activeTab === 'materials'
                    ? 'border-teal text-navy'
                    : 'border-transparent text-muted hover:text-navy',
                ]"
                @click="activeTab = 'materials'"
              >
                <FileText :size="15" aria-hidden="true" />
                <span>Tài liệu học tập</span>
                <span
                  v-if="!lessonMaterialsLoading && totalMaterialBadgeCount > 0"
                  class="rounded-full bg-teal/10 px-2 py-0.5 text-[11px] font-bold text-teal-dark tabular-nums"
                >
                  {{ totalMaterialBadgeCount }}
                </span>
              </button>
            </div>
          </div>

          <!-- TAB 1: LESSON CONTENT -->
          <div v-if="activeTab === 'content'" class="space-y-5">
            <div class="prose max-w-none">
              <p class="whitespace-pre-line text-sm leading-relaxed text-ink sm:text-base">
                {{ activeLesson.content || 'Bài học này hiện chưa có nội dung văn bản chi tiết.' }}
              </p>
            </div>

            <!-- Compact preview of direct lesson attachments -->
            <div
              v-if="directLessonMaterials.length"
              class="space-y-3 rounded-xl border border-border bg-subtle/60 p-4"
            >
              <div class="flex items-center justify-between gap-2">
                <h3 class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted">
                  <FileText :size="14" class="text-teal" aria-hidden="true" />
                  <span>Tài liệu đính kèm bài học ({{ directLessonMaterials.length }})</span>
                </h3>
                <button
                  type="button"
                  class="text-xs font-semibold text-teal hover:underline"
                  @click="activeTab = 'materials'"
                >
                  Xem tab Tài liệu
                </button>
              </div>

              <div class="grid gap-2 sm:grid-cols-2">
                <button
                  v-for="mat in directLessonMaterials"
                  :key="mat.id"
                  type="button"
                  :disabled="openingMaterialId === String(mat.id)"
                  class="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface p-2.5 text-xs font-medium text-ink transition-colors hover:border-teal hover:text-teal"
                  @click="openLessonMaterial(mat)"
                >
                  <span class="truncate">{{ mat.title }}</span>
                  <ExternalLink :size="12" class="shrink-0 text-muted" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>

          <!-- TAB 2: LEARNING MATERIALS (Direct Attachments + Lesson Recommended Materials) -->
          <div v-else class="space-y-6">
            <!-- Direct Lesson Materials -->
            <section v-if="directLessonMaterials.length" class="space-y-3">
              <h3 class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted">
                <FileText :size="14" class="text-teal" aria-hidden="true" />
                <span>Tài liệu đính kèm trực tiếp của bài học</span>
              </h3>

              <div class="grid gap-2.5 sm:grid-cols-2">
                <div
                  v-for="mat in directLessonMaterials"
                  :key="mat.id"
                  class="flex items-center justify-between gap-3 rounded-lg border border-border bg-subtle/50 p-3"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-navy">{{ mat.title }}</p>
                    <p v-if="mat.type" class="mt-0.5 text-[11px] font-medium uppercase text-muted">{{ mat.type }}</p>
                  </div>
                  <div class="flex shrink-0 items-center gap-2">
                    <RouterLink
                      :to="{ name: 'material-detail', params: { id: mat.id } }"
                      class="text-xs font-semibold text-navy hover:text-teal hover:underline"
                    >
                      Chi tiết
                    </RouterLink>
                    <button
                      v-if="mat.url"
                      type="button"
                      :disabled="openingMaterialId === String(mat.id)"
                      class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1"
                      @click="openLessonMaterial(mat)"
                    >
                      <span>{{ openingMaterialId === String(mat.id) ? 'Đang mở…' : 'Mở' }}</span>
                      <ExternalLink :size="11" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <!-- Recommended Materials for This Lesson (TF-IDF + Cosine Similarity) -->
            <section class="space-y-3">
              <div class="flex items-center justify-between gap-2">
                <h3 class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted">
                  <Sparkles :size="14" class="text-amber" aria-hidden="true" />
                  <span>Tài liệu gợi ý liên quan đến bài học này</span>
                </h3>
              </div>

              <div v-if="lessonMaterialsLoading" class="grid gap-4 sm:grid-cols-2">
                <UiSkeleton v-for="n in 2" :key="n" variant="card" />
              </div>

              <UiAlert
                v-else-if="lessonMaterialsError"
                :variant="lessonMaterialsForbidden ? 'warning' : 'danger'"
                :title="lessonMaterialsForbidden ? 'Không có quyền truy cập' : 'Không thể tải tài liệu gợi ý'"
                :message="lessonMaterialsError"
              >
                <button
                  v-if="!lessonMaterialsForbidden"
                  type="button"
                  class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
                  @click="loadLessonRecommendedMaterials(route.params.courseId, activeLesson.id)"
                >
                  <RefreshCw :size="13" aria-hidden="true" />
                  <span>Thử lại</span>
                </button>
              </UiAlert>

              <div v-else-if="lessonMaterials.length" class="grid gap-4 sm:grid-cols-2">
                <MaterialCard
                  v-for="mat in lessonMaterials"
                  :key="mat.id"
                  :material="mat"
                />
              </div>

              <UiEmptyState
                v-else-if="!directLessonMaterials.length"
                :icon="FileText"
                title="Chưa có tài liệu học tập cho bài học này"
                description="Bài học hiện chưa có tài liệu đính kèm hoặc tài liệu gợi ý phù hợp đã được phê duyệt."
              />
              <p v-else class="text-xs text-muted">
                Chưa có thêm tài liệu gợi ý bổ sung cho bài học này.
              </p>
            </section>
          </div>

          <!-- Action Footer Bar (Prev / Complete / Next) -->
          <div class="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
              :disabled="!hasPrevLesson"
              @click="goToPrev"
            >
              <ChevronLeft :size="16" aria-hidden="true" />
              <span>Bài trước</span>
            </button>

            <button
              type="button"
              :class="[
                'ui-button ui-button--sm inline-flex items-center gap-1.5',
                activeLesson.completed ? 'ui-button--outline' : 'ui-button--secondary',
              ]"
              :disabled="activeLesson.completed || savingLesson === activeLesson.id"
              @click="completeLesson(activeLesson)"
            >
              <CheckCircle2 v-if="activeLesson.completed" :size="15" class="text-success" aria-hidden="true" />
              <RefreshCw v-else-if="savingLesson === activeLesson.id" :size="15" class="animate-spin" aria-hidden="true" />
              <Check v-else :size="15" aria-hidden="true" />
              <span>{{ activeLesson.completed ? 'Đã hoàn thành' : (savingLesson === activeLesson.id ? 'Đang lưu…' : 'Đánh dấu hoàn thành') }}</span>
            </button>

            <button
              type="button"
              class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5"
              :disabled="!hasNextLesson"
              @click="goToNext"
            >
              <span>Bài tiếp</span>
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
          </div>
        </div>

        <UiEmptyState
          v-else
          title="Khóa học chưa có bài học"
          description="Nhà cung cấp chưa cập nhật nội dung bài học cho khóa học này."
        />
      </main>

      <!-- SYLLABUS SIDEBAR (Desktop Sticky Collapsible + Mobile Drawer) -->
      <aside
        :class="[
          'bento-card space-y-3 p-4',
          showDesktopSidebar ? 'lg:sticky lg:top-24 lg:block' : 'lg:hidden',
          mobileDrawerOpen
            ? 'fixed inset-x-4 top-20 z-50 block max-h-[80vh] overflow-y-auto bg-surface shadow-2xl'
            : 'hidden',
        ]"
      >
        <div class="flex items-center justify-between border-b border-border pb-3">
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-navy">
              Chương trình học
            </h3>
            <span class="text-[11px] text-muted">
              {{ course.lessons.length }} bài học
            </span>
          </div>

          <button
            v-if="mobileDrawerOpen"
            type="button"
            class="p-1 text-muted hover:text-navy lg:hidden"
            aria-label="Đóng danh sách bài học"
            @click="mobileDrawerOpen = false"
          >
            <X :size="18" aria-hidden="true" />
          </button>
        </div>

        <ol class="max-h-[60vh] space-y-1.5 overflow-y-auto">
          <li v-for="(lesson, index) in course.lessons" :key="lesson.id">
            <button
              type="button"
              :class="[
                'flex w-full items-start gap-2.5 rounded-lg border p-2.5 text-left text-xs transition-all',
                activeLessonIndex === index
                  ? 'border-teal/30 bg-teal/10 font-bold text-teal-dark shadow-sm'
                  : 'border-transparent font-medium text-ink hover:bg-subtle',
              ]"
              @click="selectLesson(index)"
            >
              <span
                v-if="lesson.completed"
                class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
                title="Đã hoàn thành"
              >
                <Check :size="11" aria-hidden="true" />
              </span>
              <span
                v-else
                :class="[
                  'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold',
                  activeLessonIndex === index ? 'bg-teal text-white' : 'bg-subtle text-muted',
                ]"
              >
                {{ index + 1 }}
              </span>

              <span class="min-w-0 flex-1 line-clamp-2 leading-snug">
                {{ lesson.title }}
              </span>
            </button>
          </li>
        </ol>
      </aside>
    </div>
  </div>
</template>
