<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Heart,
  PlayCircle,
  RefreshCw,
  ShoppingCart,
  Trash2,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { resolveMediaUrl } from '@/service/api'
import {
  commerceErrorMessage,
  fetchWishlist,
  formatVnd,
  removeFromWishlist,
} from '@/service/commerceApiService'
import {
  commerceState,
  moveWishlistCourseToCartSynced,
  showCommerceToast,
  syncLearnerCommerceState,
} from '@/service/commerceState'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const totalPages = ref(0)
const loading = ref(true)
const errorMessage = ref('')
const busyIds = ref(new Set())

const hasPagination = computed(() => totalPages.value > 1)

function setBusy(courseId, active) {
  const next = new Set(busyIds.value)
  if (active) next.add(courseId)
  else next.delete(courseId)
  busyIds.value = next
}

async function loadPage(targetPage = page.value) {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchWishlist({ page: targetPage, pageSize })
    items.value = data.items || []
    total.value = Number(data.total || 0)
    page.value = Number(data.page || targetPage)
    totalPages.value = Number(data.totalPages || 0)
    commerceState.wishlistCount = total.value
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải danh sách khóa học yêu thích.')
  } finally {
    loading.value = false
  }
}

async function handleRemove(item) {
  if (busyIds.value.has(item.maKhoaHoc)) return
  setBusy(item.maKhoaHoc, true)
  try {
    await removeFromWishlist(item.maKhoaHoc)
    showCommerceToast('Đã xóa khóa học khỏi danh sách yêu thích.', 'info')
    const nextPage = items.value.length === 1 && page.value > 1 ? page.value - 1 : page.value
    await Promise.all([loadPage(nextPage), syncLearnerCommerceState({ force: true })])
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể xóa khóa học khỏi danh sách yêu thích.')
  } finally {
    setBusy(item.maKhoaHoc, false)
  }
}

async function handleMoveToCart(item) {
  if (busyIds.value.has(item.maKhoaHoc)) return
  setBusy(item.maKhoaHoc, true)
  errorMessage.value = ''
  try {
    await moveWishlistCourseToCartSynced(item.maKhoaHoc)
    const nextPage = items.value.length === 1 && page.value > 1 ? page.value - 1 : page.value
    await loadPage(nextPage)
  } catch (error) {
    // Wishlist item is preserved by Backend on failure; show clear feedback
    errorMessage.value = commerceErrorMessage(error, 'Không thể chuyển khóa học vào giỏ hàng.')
  } finally {
    setBusy(item.maKhoaHoc, false)
  }
}

onMounted(() => {
  loadPage(1)
})
</script>

<template>
  <div class="space-y-8">
    <!-- Editorial Page Header -->
    <header class="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1.5">
        <h1 class="ui-page-title text-navy">Danh sách yêu thích</h1>
        <p class="text-sm text-slate-600">
          Lưu lại các khóa học bạn quan tâm và chuyển nhanh sang giỏ hàng khi sẵn sàng học.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span class="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy tabular-nums">
          {{ total }} khóa học
        </span>
        <RouterLink
          :to="{ name: 'course-catalog' }"
          class="ui-button ui-button--outline ui-button--sm active:scale-[0.97]"
        >
          Khám phá thêm
        </RouterLink>
      </div>
    </header>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể hoàn tất thao tác"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadPage(page)"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Đang tải danh sách yêu thích">
      <UiSkeleton v-for="i in 6" :key="i" variant="card" />
    </div>

    <!-- Empty State -->
    <UiEmptyState
      v-else-if="!items.length"
      :icon="Heart"
      title="Chưa có khóa học yêu thích nào"
      description="Nhấn biểu tượng trái tim trên bất kỳ khóa học nào để lưu lại và theo dõi sau."
      action-label="Khám phá khóa học"
      :action-route="{ name: 'course-catalog' }"
    />

    <!-- Wishlist Grid -->
    <template v-else>
      <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="item in items"
          :key="item.maYeuThich"
          class="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-surface transition-[border-color,box-shadow] duration-200 hover:border-teal/40 hover:shadow-sm"
        >
          <div class="relative h-36 w-full overflow-hidden border-b border-border/70 bg-subtle">
            <img
              v-if="item.hinhAnh"
              :src="resolveMediaUrl(item.hinhAnh)"
              :alt="item.tieuDe"
              class="h-full w-full object-cover"
              loading="lazy"
            >
            <div v-else class="flex h-full w-full items-center justify-center bg-navy/[0.04] text-navy/40">
              <GraduationCap :size="36" aria-hidden="true" />
            </div>

            <span
              v-if="item.tenDanhMuc"
              class="absolute left-3 top-3 max-w-[75%] truncate rounded-md bg-navy/90 px-2 py-0.5 text-[11px] font-semibold text-white"
            >
              {{ item.tenDanhMuc }}
            </span>
          </div>

          <div class="flex flex-1 flex-col gap-3 p-4">
            <div class="space-y-1.5">
              <h2 class="line-clamp-2 text-[15px] font-bold leading-snug text-navy">
                <RouterLink
                  :to="{ name: 'course-detail', params: { id: item.maKhoaHoc } }"
                  class="transition-colors hover:text-teal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
                >
                  {{ item.tieuDe }}
                </RouterLink>
              </h2>
              <p v-if="item.tenNhaCungCap" class="truncate text-xs text-muted">
                {{ item.tenNhaCungCap }}
              </p>
            </div>

            <!-- Status notices -->
            <div v-if="!item.khaDung" class="flex items-start gap-2 rounded-lg border border-amber/30 bg-amber/10 px-3 py-2 text-xs text-amber-dark">
              <AlertCircle :size="14" class="mt-0.5 shrink-0" aria-hidden="true" />
              <span>{{ item.lyDoKhongKhaDung || 'Khóa học hiện không còn khả dụng.' }}</span>
            </div>
            <div v-else-if="item.daSoHuu" class="inline-flex w-fit items-center gap-1.5 rounded-full bg-teal/10 px-2.5 py-1 text-xs font-semibold text-teal-dark">
              <CheckCircle2 :size="13" aria-hidden="true" />
              <span>Bạn đã sở hữu khóa học này</span>
            </div>

            <!-- Price & Actions -->
            <div class="mt-auto space-y-3 border-t border-border/80 pt-3.5">
              <div class="flex items-baseline justify-between">
                <span class="text-xs font-medium text-muted">Học phí</span>
                <span class="text-base font-bold text-navy tabular-nums">
                  {{ formatVnd(item.giaHienTai) }}
                </span>
              </div>

              <div class="flex items-center gap-2">
                <RouterLink
                  v-if="item.daSoHuu"
                  :to="{ name: 'learning', params: { courseId: item.maKhoaHoc } }"
                  class="ui-button ui-button--primary ui-button--sm flex-1 inline-flex items-center justify-center gap-1.5 active:scale-[0.97]"
                >
                  <PlayCircle :size="14" aria-hidden="true" />
                  <span>Vào học ngay</span>
                </RouterLink>

                <RouterLink
                  v-else-if="item.trongGioHang"
                  :to="{ name: 'cart' }"
                  class="ui-button ui-button--outline ui-button--sm flex-1 inline-flex items-center justify-center gap-1.5 active:scale-[0.97]"
                >
                  <ShoppingCart :size="14" class="text-teal" aria-hidden="true" />
                  <span>Đã có trong giỏ</span>
                </RouterLink>

                <RouterLink
                  v-else-if="item.khaDung && Number(item.giaHienTai) === 0"
                  :to="{ name: 'course-detail', params: { id: item.maKhoaHoc } }"
                  class="ui-button ui-button--primary ui-button--sm flex-1 inline-flex items-center justify-center gap-1.5 active:scale-[0.97]"
                >
                  <BookOpen :size="14" aria-hidden="true" />
                  <span>Đăng ký miễn phí</span>
                </RouterLink>

                <button
                  v-else-if="item.khaDung && Number(item.giaHienTai) > 0"
                  type="button"
                  class="ui-button ui-button--primary ui-button--sm flex-1 inline-flex items-center justify-center gap-1.5 active:scale-[0.97]"
                  :disabled="busyIds.has(item.maKhoaHoc)"
                  @click="handleMoveToCart(item)"
                >
                  <RefreshCw v-if="busyIds.has(item.maKhoaHoc)" :size="14" class="animate-spin" aria-hidden="true" />
                  <ShoppingCart v-else :size="14" aria-hidden="true" />
                  <span>Chuyển vào giỏ</span>
                </button>

                <button
                  v-else
                  type="button"
                  disabled
                  class="ui-button ui-button--outline ui-button--sm flex-1 opacity-60 cursor-not-allowed"
                >
                  Không khả dụng
                </button>

                <button
                  type="button"
                  class="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border text-muted transition-[background-color,color,transform] duration-150 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600 active:scale-[0.95] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
                  aria-label="Xóa khỏi danh sách yêu thích"
                  title="Xóa khỏi yêu thích"
                  :disabled="busyIds.has(item.maKhoaHoc)"
                  @click="handleRemove(item)"
                >
                  <Trash2 :size="15" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>

      <!-- Pagination -->
      <nav
        v-if="hasPagination"
        class="flex items-center justify-center gap-2 pt-2"
        aria-label="Phân trang danh sách yêu thích"
      >
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1 active:scale-[0.97]"
          :disabled="page <= 1"
          @click="loadPage(page - 1)"
        >
          <ChevronLeft :size="14" aria-hidden="true" />
          <span>Trước</span>
        </button>
        <span class="px-3 text-xs font-semibold text-navy tabular-nums">
          Trang {{ page }} / {{ totalPages }}
        </span>
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1 active:scale-[0.97]"
          :disabled="page >= totalPages"
          @click="loadPage(page + 1)"
        >
          <span>Sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </nav>
    </template>
  </div>
</template>
