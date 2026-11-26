<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clock3,
  PlayCircle,
  ReceiptText,
  RefreshCw,
  XCircle,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  commerceErrorMessage,
  fetchOrderDetail,
  formatVnd,
  generateIdempotencyKey,
  initiatePayment,
  verifyVnpayReturn,
} from '@/service/commerceApiService'
import { commerceState, syncLearnerCommerceState } from '@/service/commerceState'

const route = useRoute()
const router = useRouter()

const resolvedOrderId = ref(null)
const vnpayReturnNotice = ref('')
const hasVnpayReturnParams = computed(() => Boolean(route.query.vnp_TxnRef))
const orderId = computed(() => {
  if (resolvedOrderId.value) return resolvedOrderId.value
  const n = Number(route.query.orderId)
  return Number.isInteger(n) && n > 0 ? n : null
})

const order = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const retrying = ref(false)
const pollAttempts = ref(0)
const MAX_POLL_ATTEMPTS = 8
let pollTimer = null

const latestPayment = computed(() => order.value?.thanhToans?.[0] || null)
const needsReconciliation = computed(() => Boolean(latestPayment.value?.canDoiSoat))
const isTerminal = computed(() =>
  ['PAID', 'CANCELLED', 'EXPIRED', 'REFUNDED'].includes(String(order.value?.trangThai || '')),
)
const canRetryPayment = computed(() => {
  if (!order.value || (!commerceState.mockPaymentEnabled && !commerceState.vnpaySandboxEnabled)) return false
  if (!['PENDING', 'FAILED'].includes(order.value.trangThai)) return false
  if (needsReconciliation.value) return false
  const expiry = new Date(order.value.hanThanhToan)
  return !Number.isNaN(expiry.getTime()) && expiry.getTime() > Date.now()
})

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

async function fetchStatusFromServer({ isPoll = false } = {}) {
  if (!isPoll && hasVnpayReturnParams.value && !resolvedOrderId.value) {
    loading.value = true
    errorMessage.value = ''
    vnpayReturnNotice.value = ''
    try {
      const verify = await verifyVnpayReturn(route.query)
      if (!verify.signatureValid) {
        errorMessage.value = verify.thongDiep || 'Chữ ký URL trả về từ VNPay không hợp lệ.'
        loading.value = false
        return
      }
      if (verify.maDonHang) {
        resolvedOrderId.value = Number(verify.maDonHang)
      }
      vnpayReturnNotice.value = verify.thongDiep || ''
    } catch (error) {
      errorMessage.value = commerceErrorMessage(error, 'Không thể xác minh URL trả về từ VNPay Sandbox.')
      loading.value = false
      return
    }
  }

  if (!orderId.value) {
    errorMessage.value = 'Không tìm thấy mã đơn hàng để xác minh kết quả thanh toán.'
    loading.value = false
    return
  }
  if (!isPoll) {
    loading.value = true
  }
  errorMessage.value = ''
  try {
    const data = await fetchOrderDetail(orderId.value)
    order.value = data
    if (data.trangThai === 'PAID') {
      stopPolling()
      await syncLearnerCommerceState({ force: true })
      return
    }
    if (!isTerminal.value && data.trangThai === 'PENDING' && pollAttempts.value < MAX_POLL_ATTEMPTS) {
      pollAttempts.value += 1
      pollTimer = setTimeout(() => fetchStatusFromServer({ isPoll: true }), 2500)
    } else {
      stopPolling()
    }
  } catch (error) {
    stopPolling()
    errorMessage.value = commerceErrorMessage(error, 'Không thể xác minh trạng thái đơn hàng từ hệ thống.')
  } finally {
    loading.value = false
  }
}

async function handleManualRetry() {
  if (!order.value || retrying.value) return
  retrying.value = true
  errorMessage.value = ''
  try {
    const gateway = commerceState.vnpaySandboxEnabled ? 'VNPAY_SANDBOX' : 'MOCK_SANDBOX'
    const payment = await initiatePayment(
      order.value.maDonHang,
      gateway,
      generateIdempotencyKey('retry'),
    )
    if (payment.congThanhToan === 'VNPAY_SANDBOX' && payment.paymentUrl?.startsWith('https://sandbox.vnpayment.vn/')) {
      window.location.assign(payment.paymentUrl)
      return
    }
    await router.push({
      name: 'mock-payment',
      query: { txnRef: payment.maGiaoDichNoiBo, orderId: String(order.value.maDonHang) },
    })
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể khởi tạo lần thanh toán mới.')
  } finally {
    retrying.value = false
  }
}

onMounted(() => {
  fetchStatusFromServer()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Lỗi xác minh kết quả thanh toán"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="fetchStatusFromServer()"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Kiểm tra lại</span>
      </button>
    </UiAlert>

    <UiSkeleton v-if="loading" variant="detail" :lines="5" />

    <section v-else-if="order" class="rounded-2xl border border-border bg-surface p-6 sm:p-8 space-y-6">
      <!-- Status Header -->
      <div class="flex flex-col items-center text-center space-y-3">
        <div
          v-if="order.trangThai === 'PAID'"
          class="flex size-14 items-center justify-center rounded-full bg-teal/15 text-teal"
        >
          <CheckCircle2 :size="30" aria-hidden="true" />
        </div>
        <div
          v-else-if="needsReconciliation"
          class="flex size-14 items-center justify-center rounded-full bg-amber/15 text-amber-dark"
        >
          <AlertTriangle :size="30" aria-hidden="true" />
        </div>
        <div
          v-else-if="order.trangThai === 'PENDING'"
          class="flex size-14 items-center justify-center rounded-full bg-amber/15 text-amber-dark"
        >
          <Clock3 :size="30" aria-hidden="true" />
        </div>
        <div
          v-else-if="order.trangThai === 'CANCELLED'"
          class="flex size-14 items-center justify-center rounded-full bg-slate-100 text-slate-600"
        >
          <Ban :size="30" aria-hidden="true" />
        </div>
        <div
          v-else
          class="flex size-14 items-center justify-center rounded-full bg-rose-50 text-rose-600"
        >
          <XCircle :size="30" aria-hidden="true" />
        </div>

        <h1 class="font-display text-2xl font-bold text-navy">
          <template v-if="order.trangThai === 'PAID'">Thanh toán thành công</template>
          <template v-else-if="order.trangThai === 'REFUNDED'">Đã hoàn tiền được xác nhận</template>
          <template v-else-if="needsReconciliation">Đang đối soát giao dịch</template>
          <template v-else-if="order.trangThai === 'PENDING'">Đang xác minh giao dịch</template>
          <template v-else-if="order.trangThai === 'FAILED'">Thanh toán không thành công</template>
          <template v-else-if="order.trangThai === 'CANCELLED'">Đơn hàng đã được hủy</template>
          <template v-else-if="order.trangThai === 'EXPIRED'">Đơn hàng đã hết hạn thanh toán</template>
          <template v-else>Trạng thái đơn hàng: {{ order.trangThai }}</template>
        </h1>

        <p class="max-w-md text-sm text-slate-600">
          <template v-if="order.trangThai === 'PAID'">
            Hệ thống đã xác nhận giao dịch và cấp quyền học cho các khóa học bên dưới.
          </template>
          <template v-else-if="order.trangThai === 'REFUNDED'">
            Khoản hoàn tiền ngoại lệ cho sự cố giao dịch đã được xác nhận. Tiến độ và lịch sử học tập cũ vẫn được bảo toàn.
          </template>
          <template v-else-if="needsReconciliation">
            Giao dịch của bạn đang được đối soát bởi Quản trị viên. Vui lòng không thanh toán lại cho đến khi có kết quả xử lý.
          </template>
          <template v-else-if="order.trangThai === 'PENDING'">
            Giao dịch của bạn đang được xác minh. Vui lòng không thanh toán lại cho đến khi có kết quả.
          </template>
          <template v-else-if="order.trangThai === 'FAILED'">
            Lần thanh toán vừa rồi chưa thành công. Bạn có thể thử thanh toán lại nếu đơn hàng vẫn còn hạn hoặc báo cáo sự cố nếu tài khoản đã bị trừ tiền.
          </template>
          <template v-else-if="order.trangThai === 'CANCELLED'">
            Đơn hàng đã hủy và không phát sinh cấp quyền học.
          </template>
          <template v-else-if="order.trangThai === 'EXPIRED'">
            Đơn hàng đã quá thời hạn thanh toán. Nếu bạn đã bị trừ tiền, vui lòng gửi báo cáo sự cố tại chi tiết đơn hàng để Quản trị viên hỗ trợ.
          </template>
        </p>
      </div>

      <!-- Order Summary Meta -->
      <dl class="grid gap-3 rounded-xl border border-border/80 bg-canvas/60 p-4 text-sm sm:grid-cols-2">
        <div>
          <dt class="text-xs text-muted">Mã đơn hàng</dt>
          <dd class="mt-0.5 font-semibold text-navy tabular-nums">{{ order.maSoDonHang }}</dd>
        </div>
        <div>
          <dt class="text-xs text-muted">Số tiền</dt>
          <dd class="mt-0.5 font-bold text-navy tabular-nums">{{ formatVnd(order.tongTien) }}</dd>
        </div>
      </dl>

      <!-- Purchased Courses List -->
      <div class="space-y-2.5">
        <p class="text-xs font-semibold uppercase tracking-wider text-muted">
          Khóa học trong đơn ({{ order.items.length }})
        </p>
        <ul class="divide-y divide-border/70 rounded-xl border border-border/80 px-4">
          <li
            v-for="item in order.items"
            :key="item.maChiTietDonHang"
            class="flex flex-wrap items-center justify-between gap-3 py-3"
          >
            <div class="min-w-0">
              <p class="text-sm font-semibold text-navy">{{ item.tieuDeSnapshot }}</p>
              <p class="text-xs text-muted tabular-nums">{{ formatVnd(item.giaTaiThoiDiemMua) }}</p>
            </div>
            <RouterLink
              v-if="order.trangThai === 'PAID'"
              :to="{ name: 'learning', params: { courseId: item.maKhoaHoc } }"
              class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5 active:scale-[0.97]"
            >
              <PlayCircle :size="14" aria-hidden="true" />
              <span>Bắt đầu học</span>
            </RouterLink>
          </li>
        </ul>
      </div>

      <!-- Footer Actions -->
      <div class="flex flex-wrap items-center justify-center gap-3 border-t border-border/80 pt-5">
        <button
          v-if="canRetryPayment"
          type="button"
          class="ui-button ui-button--primary inline-flex items-center gap-2 active:scale-[0.97]"
          :disabled="retrying"
          @click="handleManualRetry"
        >
          <RefreshCw v-if="retrying" :size="15" class="animate-spin" aria-hidden="true" />
          <span>{{ retrying ? 'Đang khởi tạo…' : 'Thử thanh toán lại' }}</span>
        </button>

        <RouterLink
          v-if="order.trangThai === 'PAID'"
          :to="{ name: 'user-dashboard' }"
          class="ui-button ui-button--primary inline-flex items-center gap-2 active:scale-[0.97]"
        >
          <PlayCircle :size="15" aria-hidden="true" />
          <span>Tới Học tập của tôi</span>
        </RouterLink>

        <RouterLink
          :to="{ name: 'order-detail', params: { id: order.maDonHang } }"
          class="ui-button ui-button--outline inline-flex items-center gap-2 active:scale-[0.97]"
        >
          <ReceiptText :size="15" aria-hidden="true" />
          <span>Xem chi tiết đơn hàng</span>
        </RouterLink>
      </div>
    </section>
  </div>
</template>
