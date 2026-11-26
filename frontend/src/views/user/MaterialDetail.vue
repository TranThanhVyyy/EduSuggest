<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckCircle,
  ChevronRight,
  Clock,
  Download,
  ExternalLink,
  FileText,
  GraduationCap,
  Layers,
  Lock,
  LogIn,
  Sparkles,
  Tag,
} from 'lucide-vue-next'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import MaterialCard from '@/components/user/MaterialCard.vue'
import { authState } from '@/service/authState'
import { getRoleName } from '@/service/authService'
import { fetchPublicMaterial, fetchSimilarMaterials } from '@/service/userApiService'
import { openMaterialFile } from '@/service/materialFileService'

const route = useRoute()
const materialId = computed(() => route.params.id)
const isAuthenticated = computed(() => Boolean(authState.accessToken && authState.user))
const isLearner = computed(() => isAuthenticated.value && getRoleName() === 'USER')
const displayProvider = computed(() => {
  const raw = String(material.value?.providerName || material.value?.provider || '').trim()
  if (!raw || raw === 'Chưa có thông tin' || /^Nhà cung cấp #\d+$/.test(raw)) {
    return 'Thông tin nhà cung cấp chưa được cập nhật'
  }
  return raw
})

const material = ref(null)
const similarMaterials = ref([])
const loading = ref(true)
const error = ref('')
const fileError = ref('')
const openingFile = ref(false)

async function accessMaterial(download = false) {
  openingFile.value = true
  fileError.value = ''
  try {
    await openMaterialFile(material.value, { download })
  } catch (cause) {
    fileError.value = cause.response?.data?.detail || 'Không thể mở tệp. Quyền truy cập có thể đã thay đổi.'
  } finally {
    openingFile.value = false
  }
}

async function loadData() {
  if (!materialId.value) return
  loading.value = true
  error.value = ''
  material.value = null
  similarMaterials.value = []

  try {
    const mat = await fetchPublicMaterial(materialId.value)
    material.value = mat
    if (isLearner.value) {
      const similar = await fetchSimilarMaterials(materialId.value, { limit: 4 }).catch(() => [])
      similarMaterials.value = similar.filter((item) => String(item.id) !== String(materialId.value))
    }
  } catch (cause) {
    error.value = cause.response?.data?.detail || 'Không thể tải chi tiết tài liệu học tập.'
  } finally {
    loading.value = false
  }
}

watch(materialId, loadData, { immediate: true })
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <!-- Semantic Breadcrumb Navigation -->
    <nav aria-label="Điều hướng">
      <ol class="flex flex-wrap items-center gap-1.5 text-xs font-semibold text-muted">
        <li>
          <RouterLink
            :to="{ name: 'material-catalog' }"
            class="inline-flex items-center gap-1.5 text-teal hover:underline"
          >
            <ArrowLeft :size="14" aria-hidden="true" />
            <span>Thư viện tài liệu</span>
          </RouterLink>
        </li>
        <template v-if="material?.categoryName && material?.categoryId">
          <li aria-hidden="true">
            <ChevronRight :size="13" class="text-slate-500" />
          </li>
          <li>
            <RouterLink
              :to="{ name: 'material-catalog', query: { category_id: String(material.categoryId) } }"
              class="text-muted transition-colors duration-150 hover:text-teal hover:underline"
            >
              {{ material.categoryName }}
            </RouterLink>
          </li>
        </template>
        <li aria-hidden="true">
          <ChevronRight :size="13" class="text-slate-500" />
        </li>
        <li
          aria-current="page"
          class="max-w-[220px] truncate text-ink sm:max-w-[360px]"
        >
          {{ material?.title || 'Chi tiết tài liệu' }}
        </li>
      </ol>
    </nav>

    <!-- Error Alert -->
    <UiAlert
      v-if="error"
      variant="danger"
      :message="error"
      dismissible
      @dismiss="error = ''"
    />

    <!-- Skeleton Loading -->
    <div v-if="loading" class="space-y-4">
      <div class="bento-card p-6 bg-surface">
        <UiSkeleton variant="detail" :lines="6" />
      </div>
    </div>

    <!-- Empty / Not Found -->
    <div v-else-if="!material" class="bento-card p-8 bg-surface">
      <UiEmptyState
        title="Tài liệu không khả dụng"
        description="Tài liệu bạn yêu cầu không tồn tại hoặc chưa được phê duyệt hiển thị công khai."
        action-label="Khám phá tài liệu khác"
        @action="$router.push({ name: 'material-catalog' })"
      />
    </div>

    <!-- Material Content (Editorial Modernism) -->
    <template v-else>
      <article class="bento-card p-6 sm:p-8 bg-surface space-y-6">
        <!-- Top Tags & Eyebrow -->
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="rounded px-2.5 py-0.5 font-bold uppercase tracking-wider bg-teal/10 text-teal border border-teal/20">
            {{ material.type || 'DOCUMENT' }}
          </span>
          <span
            v-if="material.categoryName"
            class="rounded px-2.5 py-0.5 font-medium bg-subtle text-slate-700 border border-border"
          >
            {{ material.categoryName }}
          </span>
          <RouterLink
            v-if="material.courseId"
            :to="{ name: 'course-detail', params: { id: material.courseId } }"
            class="rounded px-2.5 py-0.5 font-medium bg-navy/5 text-navy border border-navy/15 transition-colors duration-150 hover:border-teal/40 hover:text-teal"
          >
            Thuộc khóa học liên kết
          </RouterLink>
        </div>

        <!-- Title -->
        <header class="space-y-2">
          <h1 class="ui-page-title text-navy">
            {{ material.title }}
          </h1>
          <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600">
            <span class="inline-flex items-center gap-1.5 font-medium text-ink">
              <GraduationCap :size="14" class="text-teal" aria-hidden="true" />
              <span>{{ displayProvider }}</span>
            </span>
            <span v-if="material.createdAt" class="inline-flex items-center gap-1.5">
              <Calendar :size="13" aria-hidden="true" />
              <span>Ngày đăng: {{ new Date(material.createdAt).toLocaleDateString('vi-VN') }}</span>
            </span>
          </div>
        </header>

        <!-- Description -->
        <div class="border-t border-border/80 pt-5 space-y-3">
          <h2 class="text-xs font-bold uppercase tracking-wider text-muted">
            Mô tả & Hướng dẫn sử dụng
          </h2>
          <p class="whitespace-pre-line text-sm sm:text-base leading-relaxed text-ink/90">
            {{ material.description || 'Chưa có thông tin mô tả chi tiết cho tài liệu này.' }}
          </p>
        </div>

        <!-- Action / Download Card -->
        <div class="rounded-xl border border-teal/30 bg-teal/5 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="space-y-1">
            <p class="text-sm font-bold text-navy flex items-center gap-2">
              <CheckCircle v-if="material.fileUrl" :size="16" class="text-teal" aria-hidden="true" />
              <Lock v-else :size="16" class="text-amber" aria-hidden="true" />
              <span>
                {{
                  material.fileUrl
                    ? 'Tài liệu đã được xác thực học thuật'
                    : !isAuthenticated
                      ? 'Đăng nhập để mở hoặc tải tệp tài liệu'
                      : material.courseId
                        ? 'Tài liệu dành cho học viên đã đăng ký khóa học'
                        : 'Tài liệu chưa có liên kết tệp'
                }}
              </span>
            </p>
            <p class="text-xs text-muted">
              {{
                material.fileUrl
                  ? 'Có thể tải về hoặc xem trực tuyến theo liên kết nhà cung cấp cung cấp.'
                  : !isAuthenticated
                    ? 'Bạn đang xem thông tin công khai của tài liệu. Vui lòng đăng nhập tài khoản học viên để truy cập nội dung tệp.'
                    : material.courseId
                      ? 'Tài liệu này thuộc khóa học liên kết. Hãy đăng ký khóa học để mở khóa tệp học tập.'
                      : 'Nhà cung cấp chưa đính kèm liên kết tệp cho tài liệu này.'
              }}
            </p>
          </div>

          <button
            v-if="material.fileUrl"
            type="button"
            :disabled="openingFile"
            class="ui-button ui-button--primary inline-flex items-center justify-center gap-2 text-xs sm:text-sm shrink-0"
            @click="accessMaterial(false)"
          >
            <Download :size="15" aria-hidden="true" />
            <span>{{ openingFile ? 'Đang xác thực…' : 'Mở / Tải tài liệu' }}</span>
            <ExternalLink :size="13" class="opacity-75" aria-hidden="true" />
          </button>

          <RouterLink
            v-else-if="!isAuthenticated"
            :to="{ name: 'login', query: { redirect: route.fullPath } }"
            class="ui-button ui-button--primary inline-flex items-center justify-center gap-2 text-xs sm:text-sm shrink-0"
          >
            <LogIn :size="15" aria-hidden="true" />
            <span>Đăng nhập để truy cập</span>
          </RouterLink>

          <RouterLink
            v-else-if="material.courseId"
            :to="{ name: 'course-detail', params: { id: material.courseId } }"
            class="ui-button ui-button--outline inline-flex items-center justify-center gap-2 text-xs sm:text-sm shrink-0"
          >
            <BookOpen :size="15" aria-hidden="true" />
            <span>Xem khóa học liên kết</span>
          </RouterLink>

          <span v-else class="text-xs text-muted font-medium">
            Chưa có liên kết tệp
          </span>
        </div>

        <UiAlert v-if="fileError" variant="danger" title="Không thể truy cập tệp" :message="fileError" />
      </article>

      <!-- Similar Recommended Materials Section -->
      <section v-if="similarMaterials.length" class="space-y-4 pt-4">
        <div class="flex items-center gap-2">
          <Sparkles :size="18" class="text-amber" aria-hidden="true" />
          <h2 class="text-lg font-bold text-navy">Tài liệu tương tự được gợi ý (TF-IDF)</h2>
        </div>
        <p class="text-xs text-muted">
          Được phân tích độ tương đồng nội dung dựa trên vector ngữ nghĩa thuật toán TF-IDF & Cosine Similarity.
        </p>

        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MaterialCard
            v-for="sim in similarMaterials"
            :key="sim.id"
            :material="sim"
          />
        </div>
      </section>
    </template>
  </div>
</template>
