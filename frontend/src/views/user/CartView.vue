<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowRight,
  GraduationCap,
  RefreshCw,
  ShoppingCart,
  Trash2,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { resolveMediaUrl } from '@/service/api'
import {
  clearCart,
  commerceErrorMessage,
  fetchCart,
  formatVnd,
} from '@/service/commerceApiService'
import {
  commerceState,
  removeCourseFromCartSynced,
  showCommerceToast,
} from '@/service/commerceState'

const router = useRouter()

const cart = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const selectedIds = ref(new Set())
const busyItemIds = ref(new Set())
const clearing = ref(false)
const confirmClearOpen = ref(false)

const items = computed(() => cart.value?.items || [])
const validItems = computed(() => items.value.filter((i) => i.khaDung))
const allValidSelected = computed(
  () => validItems.value.length > 0 && validItems.value.every((i) => selectedIds.value.has(i.maKhoaHoc)),
)

const selectedItems = computed(() =>
  validItems.value.filter((i) => selectedIds.value.has(i.maKhoaHoc)),
)

// Display-only estimate from Backend's live giaHienTai; Checkout always re-verifies via POST /api/orders/preview
const selectedEstimatedTotal = computed(() =>
  selectedItems.value.reduce((sum, item) => sum + Number(item.giaHienTai || 0), 0),
)

function syncFromResponse(data) {
  cart.value = data
  const nextIds = new Set((data.items || []).map((i) => Number(i.maKhoaHoc)))
  commerceState.cartIds = nextIds
  commerceState.cartCount = Number(data.tongSoLuong ?? nextIds.size)
  commerceState.cartValidCount = Number(data.soLuongHopLe ?? 0)

  // Keep valid selections; default-select all valid items on initial load
  const validSet = new Set((data.items || []).filter((i) => i.khaDung).map((i) => i.maKhoaHoc))
  if (selectedIds.value.size === 0) {
    selectedIds.value = validSet
  } else {
    selectedIds.value = new Set([...selectedIds.value].filter((id) => validSet.has(id)))
  }
}

async function loadCart() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchCart()
    selectedIds.value = new Set()
    syncFromResponse(data)
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải giỏ hàng.')
  } finally {
    loading.value = false
  }
}

function toggleSelectAll() {
  if (allValidSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(validItems.value.map((i) => i.maKhoaHoc))
  }
}

function toggleItem(courseId) {
  const next = new Set(selectedIds.value)
  if (next.has(courseId)) next.delete(courseId)
  else next.add(courseId)
  selectedIds.value = next
}

async function handleRemove(courseId) {
  if (busyItemIds.value.has(courseId)) return
  const nextBusy = new Set(busyItemIds.value)
  nextBusy.add(courseId)
  busyItemIds.value = nextBusy
  try {
    const data = await removeCourseFromCartSynced(courseId)
    syncFromResponse(data)
    showCommerceToast('Đã xóa khóa học khỏi giỏ hàng.', 'info')
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể xóa khóa học khỏi giỏ hàng.')
  } finally {
    const clean = new Set(busyItemIds.value)
    clean.delete(courseId)
    busyItemIds.value = clean
  }
}

async function handleClearAll() {
  if (clearing.value) return
  clearing.value = true
  errorMessage.value = ''
  try {
    await clearCart()
    confirmClearOpen.value = false
    selectedIds.value = new Set()
    await loadCart()
    showCommerceToast('Đã xóa toàn bộ giỏ hàng.', 'info')
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể xóa toàn bộ giỏ hàng.')
  } finally {
    clearing.value = false
  }
}

function proceedToCheckout() {
  if (!selectedItems.value.length) return
  const ids = selectedItems.value.map((i) => i.maKhoaHoc).join(',')
  router.push({
    name: 'checkout',
    query: { source: 'CART', courseIds: ids },
  })
}

onMounted(() => {
  loadCart()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <header class="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1.5">
        <h1 class="ui-page-title text-navy">Giỏ hàng của bạn</h1>
        <p class="text-sm text-slate-600">
          Chọn các khóa học muốn thanh toán. Học phí luôn được xác nhận lại trực tiếp từ hệ thống trước khi tạo đơn.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2.5">
        <RouterLink
          :to="{ name: 'course-catalog' }"
          class="ui-button ui-button--outline ui-button--sm active:scale-[0.97]"
        >
          Tiếp tục khám phá
        </RouterLink>
        <button
          v-if="items.length && !confirmClearOpen"
          type="button"
          class="ui-button ui-button--outline ui-button--sm text-rose-700 hover:border-rose-300 hover:bg-rose-50 active:scale-[0.97]"
          @click="confirmClearOpen = true"
        >
          Xóa toàn bộ
        </button>
      </div>
    </header>

    <!-- Inline Clear Cart Confirmation -->
    <div
      v-if="confirmClearOpen"
      class="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50/70 p-4 sm:flex-row sm:items-center sm:justify-between"
      role="alert"
    >
      <p class="text-sm font-medium text-rose-900">
        Bạn có chắc muốn xóa tất cả {{ items.length }} khóa học khỏi giỏ hàng?
      </p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm bg-surface"
          :disabled="clearing"
          @click="confirmClearOpen = false"
        >
          Giữ lại
        </button>
        <button
          type="button"
          class="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-rose-700 active:scale-[0.97]"
          :disabled="clearing"
          @click="handleClearAll"
        >
          {{ clearing ? 'Đang xóa…' : 'Xác nhận xóa' }}
        </button>
      </div>
    </div>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể tải giỏ hàng"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadCart"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-6 lg:grid-cols-12" role="status" aria-label="Đang tải giỏ hàng">
      <div class="space-y-4 lg:col-span-8">
        <UiSkeleton v-for="i in 3" :key="i" variant="detail" :lines="3" />
      </div>
      <div class="lg:col-span-4">
        <UiSkeleton variant="card" />
      </div>
    </div>

    <!-- Empty -->
    <UiEmptyState
      v-else-if="!items.length"
      :icon="ShoppingCart"
      title="Giỏ hàng đang trống"
      description="Khám phá danh mục khóa học đã kiểm duyệt và thêm các khóa học phù hợp với mục tiêu của bạn."
      action-label="Khám phá khóa học"
      :action-route="{ name: 'course-catalog' }"
    />

    <!-- Two-Column Bento Cart Layout -->
    <div v-else class="grid items-start gap-6 lg:grid-cols-12">
      <!-- Left: Cart Items -->
      <section class="space-y-4 lg:col-span-8" aria-label="Danh sách khóa học trong giỏ">
        <UiAlert
          v-if="cart?.coThayDoiGia"
          variant="warning"
          title="Học phí có thay đổi"
          message="Một số khóa học trong giỏ vừa được cập nhật học phí. Tổng thanh toán sẽ tính theo giá hiện hành từ hệ thống."
        />
        <UiAlert
          v-if="cart?.coMucKhongHopLe"
          variant="warning"
          title="Có khóa học không còn khả dụng"
          message="Các khóa học tạm ẩn hoặc đã sở hữu sẽ tự động loại khỏi tổng tiền thanh toán."
        />

        <!-- Select All Bar -->
        <div class="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3">
          <label class="inline-flex cursor-pointer items-center gap-2.5 text-sm font-semibold text-navy">
            <input
              type="checkbox"
              :checked="allValidSelected"
              :disabled="!validItems.length"
              class="size-4 rounded border-border text-teal focus:ring-teal"
              @change="toggleSelectAll"
            >
            <span>Chọn tất cả khóa học hợp lệ ({{ validItems.length }}/{{ items.length }})</span>
          </label>
          <span class="text-xs text-muted tabular-nums">
            Đã chọn {{ selectedItems.length }}
          </span>
        </div>

        <!-- Item Rows -->
        <ul class="space-y-3">
          <li
            v-for="item in items"
            :key="item.maChiTietGioHang"
            :class="[
              'rounded-xl border bg-surface p-4 transition-colors duration-150',
              item.khaDung ? 'border-border hover:border-teal/40' : 'border-amber/40 bg-amber/[0.04]',
            ]"
          >
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div class="flex items-start gap-3">
                <input
                  type="checkbox"
                  :checked="selectedIds.has(item.maKhoaHoc)"
                  :disabled="!item.khaDung"
                  :aria-label="`Chọn khóa học ${item.tieuDe}`"
                  class="mt-1 size-4 shrink-0 rounded border-border text-teal focus:ring-teal disabled:opacity-40"
                  @change="toggleItem(item.maKhoaHoc)"
                >
                <div class="h-20 w-32 shrink-0 overflow-hidden rounded-lg border border-border/70 bg-subtle">
                  <img
                    v-if="item.hinhAnh"
                    :src="resolveMediaUrl(item.hinhAnh)"
                    :alt="item.tieuDe"
                    class="h-full w-full object-cover"
                    loading="lazy"
                  >
                  <div v-else class="flex h-full w-full items-center justify-center text-navy/35">
                    <GraduationCap :size="24" aria-hidden="true" />
                  </div>
                </div>
              </div>

              <div class="min-w-0 flex-1 space-y-1.5">
                <RouterLink
                  :to="{ name: 'course-detail', params: { id: item.maKhoaHoc } }"
                  class="line-clamp-2 text-sm font-bold text-navy transition-colors hover:text-teal sm:text-[15px]"
                >
                  {{ item.tieuDe }}
                </RouterLink>
                <p v-if="item.tenNhaCungCap || item.tenDanhMuc" class="text-xs text-muted">
                  <span v-if="item.tenNhaCungCap">{{ item.tenNhaCungCap }}</span>
                  <span v-if="item.tenNhaCungCap && item.tenDanhMuc"> · </span>
                  <span v-if="item.tenDanhMuc">{{ item.tenDanhMuc }}</span>
                </p>

                <div
                  v-if="!item.khaDung"
                  class="inline-flex items-center gap-1.5 rounded-md bg-amber/15 px-2.5 py-1 text-xs font-medium text-amber-dark"
                >
                  <AlertTriangle :size="13" aria-hidden="true" />
                  <span>{{ item.lyDoKhongKhaDung || 'Không thể thanh toán khóa học này.' }}</span>
                </div>
                <div
                  v-else-if="item.giaThayDoi"
                  class="inline-flex items-center gap-1.5 rounded-md bg-amber/10 px-2.5 py-1 text-xs font-medium text-amber-dark tabular-nums"
                >
                  <span>Giá lúc thêm: {{ formatVnd(item.giaLucThem) }} → Hiện tại: {{ formatVnd(item.giaHienTai) }}</span>
                </div>
              </div>

              <div class="flex items-center justify-between gap-3 sm:flex-col sm:items-end">
                <p class="text-base font-bold text-navy tabular-nums">
                  {{ formatVnd(item.giaHienTai) }}
                </p>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-muted transition-colors hover:bg-rose-50 hover:text-rose-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/40"
                  :disabled="busyItemIds.has(item.maKhoaHoc)"
                  @click="handleRemove(item.maKhoaHoc)"
                >
                  <Trash2 :size="14" aria-hidden="true" />
                  <span>Xóa</span>
                </button>
              </div>
            </div>
          </li>
        </ul>
      </section>

      <!-- Right: Sticky Order Summary -->
      <aside class="lg:sticky lg:top-24 lg:col-span-4">
        <div class="rounded-2xl border border-border bg-surface p-6 space-y-5">
          <h2 class="font-display text-lg font-bold text-navy">Tóm tắt đơn hàng</h2>

          <dl class="space-y-3 border-y border-border/80 py-4 text-sm">
            <div class="flex items-center justify-between">
              <dt class="text-slate-600">Khóa học đã chọn</dt>
              <dd class="font-semibold text-navy tabular-nums">{{ selectedItems.length }} khóa học</dd>
            </div>
            <div class="flex items-baseline justify-between">
              <dt class="font-semibold text-navy">Tạm tính</dt>
              <dd class="text-xl font-bold text-navy tabular-nums">
                {{ formatVnd(selectedEstimatedTotal) }}
              </dd>
            </div>
          </dl>

          <p class="text-xs leading-relaxed text-muted">
            Tổng thanh toán chính thức bằng VND sẽ được Backend kiểm tra và chốt snapshot ở bước tiếp theo.
          </p>

          <button
            type="button"
            class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
            :disabled="!selectedItems.length"
            @click="proceedToCheckout"
          >
            <span>Tiến hành thanh toán</span>
            <ArrowRight :size="15" aria-hidden="true" />
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>
