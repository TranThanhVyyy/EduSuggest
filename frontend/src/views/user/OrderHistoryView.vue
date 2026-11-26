<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  ReceiptText,
  RefreshCw,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  commerceErrorMessage,
  fetchOrders,
  formatVnd,
  generateIdempotencyKey,
  initiatePayment,
} from '@/service/commerceApiService'
import { commerceState } from '@/service/commerceState'

const router = useRouter()

const STATUS_FILTERS = [
  { key: '', label: 'Tất cả' },
  { key: 'PENDING', label: 'Chờ thanh toán' },
  { key: 'PAID', label: 'Đã thanh toán' },
  { key: 'FAILED', label: 'Thất bại' },
  { key: 'CANCELLED', label: 'Đã hủy' },
  { key: 'EXPIRED', label: 'Hết hạn' },
]

const STATUS_STYLE = {
  PAID: { label: 'Đã thanh toán', cls: 'bg-teal/10 text-teal-dark border-teal/25' },
  PENDING: { label: 'Chờ thanh toán', cls: 'bg-amber/10 text-amber-dark border-amber/30' },
  FAILED: { label: 'Thất bại', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
  CANCELLED: { label: 'Đã hủy', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  EXPIRED: { label: 'Hết hạn', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  REFUNDED: { label: 'Đã hoàn tiền', cls: 'bg-purple-50 text-purple-700 border-purple-200' },
}

const orders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const totalPages = ref(0)
const statusFilter = ref('')
const loading = ref(true)
const errorMessage = ref('')
const payingOrderId = ref(null)

const hasPagination = computed(() => totalPages.value > 1)

function statusMeta(status) {
  return STATUS_STYLE[status] || { label: status, cls: 'bg-slate-100 text-slate-700 border-slate-200' }
}

function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function canResumePayment(order) {
  if (!commerceState.mockPaymentEnabled) return false
  if (!['PENDING', 'FAILED'].includes(order.trangThai)) return false
  const expiry = new Date(order.hanThanhToan)
  return !Number.isNaN(expiry.getTime()) && expiry.getTime() > Date.now()
}

async function loadOrders(targetPage = page.value) {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchOrders({
      page: targetPage,
      pageSize,
      trangThai: statusFilter.value,
    })
    orders.value = data.items || []
    total.value = Number(data.total || 0)
    page.value = Number(data.page || targetPage)
    totalPages.value = Number(data.totalPages || 0)
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải lịch sử mua hàng.')
  } finally {
    loading.value = false
  }
}

function selectFilter(key) {
  statusFilter.value = key
  loadOrders(1)
}

async function resumePayment(order) {
  if (payingOrderId.value) return
  payingOrderId.value = order.maDonHang
  errorMessage.value = ''
  try {
    const payment = await initiatePayment(
      order.maDonHang,
      'MOCK_SANDBOX',
      generateIdempotencyKey('resume'),
    )
    await router.push({
      name: 'mock-payment',
      query: { txnRef: payment.maGiaoDichNoiBo, orderId: String(order.maDonHang) },
    })
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tiếp tục thanh toán đơn hàng.')
  } finally {
    payingOrderId.value = null
  }
}

onMounted(() => {
  loadOrders(1)
})
</script>

<template>
  <div class="space-y-8">
    <header class="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1.5">
        <h1 class="ui-page-title text-navy">Lịch sử mua hàng</h1>
        <p class="text-sm text-slate-600">
          Theo dõi toàn bộ đơn hàng, trạng thái thanh toán và khóa học bạn đã sở hữu.
        </p>
      </div>
      <span class="w-fit rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-navy tabular-nums">
        {{ total }} đơn hàng
      </span>
    </header>

    <!-- Status Filter Tabs -->
    <div class="flex flex-wrap items-center gap-2" role="tablist" aria-label="Lọc đơn hàng theo trạng thái">
      <button
        v-for="tab in STATUS_FILTERS"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="statusFilter === tab.key"
        :class="[
          'rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors duration-150 active:scale-[0.97]',
          statusFilter === tab.key
            ? 'bg-navy text-white'
            : 'border border-border bg-surface text-slate-600 hover:border-teal/40 hover:text-navy',
        ]"
        @click="selectFilter(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể tải lịch sử mua hàng"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadOrders(page)"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <div v-if="loading" class="space-y-3" role="status" aria-label="Đang tải đơn hàng">
      <UiSkeleton v-for="i in 3" :key="i" variant="detail" :lines="3" />
    </div>

    <UiEmptyState
      v-else-if="!orders.length"
      :icon="ReceiptText"
      title="Chưa có đơn hàng nào"
      description="Các đơn hàng bạn tạo khi mua khóa học sẽ xuất hiện tại đây."
      action-label="Khám phá khóa học"
      :action-route="{ name: 'course-catalog' }"
    />

    <template v-else>
      <ul class="space-y-4">
        <li
          v-for="order in orders"
          :key="order.maDonHang"
          class="rounded-2xl border border-border bg-surface p-5 transition-colors hover:border-teal/40"
        >
          <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div class="space-y-1.5">
              <div class="flex flex-wrap items-center gap-2.5">
                <span class="font-display text-base font-bold text-navy tabular-nums">
                  {{ order.maSoDonHang }}
                </span>
                <span
                  :class="[
                    'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold',
                    statusMeta(order.trangThai).cls,
                  ]"
                >
                  {{ statusMeta(order.trangThai).label }}
                </span>
              </div>

              <p class="text-xs text-muted tabular-nums">
                Tạo lúc {{ formatDateTime(order.ngayTao) }} · {{ order.items.length }} khóa học
              </p>

              <p
                v-if="canResumePayment(order)"
                class="inline-flex items-center gap-1 text-xs font-medium text-amber-dark tabular-nums"
              >
                <Clock3 :size="13" aria-hidden="true" />
                <span>Hạn thanh toán: {{ formatDateTime(order.hanThanhToan) }}</span>
              </p>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3 sm:justify-end">
              <p class="text-lg font-bold text-navy tabular-nums">
                {{ formatVnd(order.tongTien) }}
              </p>

              <div class="flex items-center gap-2">
                <button
                  v-if="canResumePayment(order)"
                  type="button"
                  class="ui-button ui-button--primary ui-button--sm active:scale-[0.97]"
                  :disabled="payingOrderId === order.maDonHang"
                  @click="resumePayment(order)"
                >
                  {{ payingOrderId === order.maDonHang ? 'Đang chuyển…' : 'Tiếp tục thanh toán' }}
                </button>
                <RouterLink
                  :to="{ name: 'order-detail', params: { id: order.maDonHang } }"
                  class="ui-button ui-button--outline ui-button--sm active:scale-[0.97]"
                >
                  Xem chi tiết
                </RouterLink>
              </div>
            </div>
          </div>
        </li>
      </ul>

      <nav
        v-if="hasPagination"
        class="flex items-center justify-center gap-2 pt-2"
        aria-label="Phân trang lịch sử đơn hàng"
      >
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1"
          :disabled="page <= 1"
          @click="loadOrders(page - 1)"
        >
          <ChevronLeft :size="14" aria-hidden="true" />
          <span>Trước</span>
        </button>
        <span class="px-3 text-xs font-semibold text-navy tabular-nums">
          Trang {{ page }} / {{ totalPages }}
        </span>
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1"
          :disabled="page >= totalPages"
          @click="loadOrders(page + 1)"
        >
          <span>Sau</span>
          <ChevronRight :size="14" aria-hidden="true" />
        </button>
      </nav>
    </template>
  </div>
</template>
