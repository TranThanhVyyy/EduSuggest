<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  Clock3,
  GraduationCap,
  Lock,
  RefreshCw,
  ShieldCheck,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { resolveMediaUrl } from '@/service/api'
import {
  commerceErrorMessage,
  createOrder,
  formatVnd,
  generateIdempotencyKey,
  initiatePayment,
  previewOrder,
} from '@/service/commerceApiService'
import { commerceState, loadCommerceCapabilities } from '@/service/commerceState'

const route = useRoute()
const router = useRouter()

const source = computed(() =>
  String(route.query.source || 'CART').toUpperCase() === 'BUY_NOW' ? 'BUY_NOW' : 'CART',
)
const buyNowCourseId = computed(() => {
  const n = Number(route.query.courseId)
  return Number.isInteger(n) && n > 0 ? n : null
})
const selectedCourseIds = computed(() => {
  const raw = String(route.query.courseIds || '').trim()
  if (!raw) return null
  const ids = raw
    .split(',')
    .map((x) => Number(x.trim()))
    .filter((n) => Number.isInteger(n) && n > 0)
  return ids.length ? ids : null
})

const preview = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const priceChangedNotice = ref('')
const submitting = ref(false)
const redirectingToGateway = ref(false)
const paymentMethod = ref('')

const availablePaymentMethods = computed(() => {
  const list = []
  if (commerceState.mockPaymentEnabled) {
    list.push({
      code: 'MOCK_SANDBOX',
      title: 'Thanh toán mô phỏng (Sandbox)',
      badge: 'Nội bộ kiểm thử',
      description: 'Dành riêng cho môi trường kiểm thử — không thu tiền thật, không yêu cầu thông tin thẻ ngân hàng hay CVV.',
    })
  }
  if (commerceState.vnpaySandboxEnabled) {
    list.push({
      code: 'VNPAY_SANDBOX',
      title: 'VNPay Sandbox (Thử nghiệm)',
      badge: 'Môi trường thử nghiệm',
      description: 'Chuyển hướng sang cổng thử nghiệm VNPay Sandbox (không phát sinh giao dịch tiền thật). Quyền học chỉ cấp khi IPN xác nhận.',
    })
  }
  return list
})

const hasAvailablePaymentMethod = computed(() => availablePaymentMethods.value.length > 0)

// Stable Idempotency-Keys per checkout intent (reused on retry of the same request!)
const orderIdemKey = ref(generateIdempotencyKey('ord'))
const paymentIdemKey = ref(generateIdempotencyKey('pay'))
const createdOrder = ref(null)

function buildOrderPayload({ includeConfirmedTotal = false } = {}) {
  const payload = { nguonTao: source.value }
  if (source.value === 'BUY_NOW') {
    payload.maKhoaHoc = buyNowCourseId.value
  } else if (selectedCourseIds.value) {
    payload.courseIds = selectedCourseIds.value
  }
  if (includeConfirmedTotal && preview.value?.tongTien) {
    payload.tongTienXacNhan = String(preview.value.tongTien)
  }
  return payload
}

async function loadPreview() {
  loading.value = true
  errorMessage.value = ''
  priceChangedNotice.value = ''
  try {
    await loadCommerceCapabilities()
    if (!availablePaymentMethods.value.some((m) => m.code === paymentMethod.value)) {
      paymentMethod.value = availablePaymentMethods.value[0]?.code || ''
    }
    preview.value = await previewOrder(buildOrderPayload())
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải thông tin đơn hàng để thanh toán.')
  } finally {
    loading.value = false
  }
}

async function handleConfirmAndPay() {
  if (submitting.value || !preview.value || !hasAvailablePaymentMethod.value || !paymentMethod.value) return
  submitting.value = true
  errorMessage.value = ''
  priceChangedNotice.value = ''

  try {
    let order = createdOrder.value
    if (!order) {
      order = await createOrder(
        buildOrderPayload({ includeConfirmedTotal: true }),
        orderIdemKey.value,
      )
      createdOrder.value = order
    }

    const payment = await initiatePayment(
      order.maDonHang,
      paymentMethod.value,
      paymentIdemKey.value,
    )

    if (payment.congThanhToan === 'VNPAY_SANDBOX' && payment.paymentUrl?.startsWith('https://sandbox.vnpayment.vn/')) {
      redirectingToGateway.value = true
      window.location.assign(payment.paymentUrl)
      return
    }

    // Navigate to internal Mock Sandbox Simulator (server-verified session)
    await router.push({
      name: 'mock-payment',
      query: { txnRef: payment.maGiaoDichNoiBo, orderId: String(order.maDonHang) },
    })
  } catch (error) {
    if (error?.response?.status === 409) {
      // Price changed between preview and create -> refresh preview & require explicit re-confirmation
      priceChangedNotice.value = commerceErrorMessage(
        error,
        'Giá khóa học vừa thay đổi. Hệ thống đã tải lại giá mới — vui lòng kiểm tra và xác nhận lại.',
      )
      createdOrder.value = null
      orderIdemKey.value = generateIdempotencyKey('ord')
      paymentIdemKey.value = generateIdempotencyKey('pay')
      await loadPreview()
    } else {
      errorMessage.value = commerceErrorMessage(error, 'Không thể khởi tạo giao dịch thanh toán.')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadPreview()
})
</script>

<template>
  <div class="space-y-8">
    <div class="space-y-2 border-b border-border/80 pb-6">
      <RouterLink
        :to="source === 'CART' ? { name: 'cart' } : { name: 'course-catalog' }"
        class="inline-flex items-center gap-1.5 text-xs font-semibold text-teal hover:underline"
      >
        <ArrowLeft :size="14" aria-hidden="true" />
        <span>{{ source === 'CART' ? 'Quay lại giỏ hàng' : 'Quay lại khóa học' }}</span>
      </RouterLink>
      <h1 class="ui-page-title text-navy">Xác nhận &amp; thanh toán</h1>
      <p class="text-sm text-slate-600">
        Kiểm tra danh sách khóa học và tổng học phí được Backend xác nhận trước khi chuyển sang cổng thanh toán.
      </p>
    </div>

    <UiAlert
      v-if="priceChangedNotice"
      variant="warning"
      title="Học phí đã thay đổi — cần xác nhận lại"
      :message="priceChangedNotice"
    />

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể tiến hành thanh toán"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadPreview"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Tải lại thông tin</span>
      </button>
    </UiAlert>

    <div v-if="loading" class="grid gap-6 lg:grid-cols-12" role="status" aria-label="Đang chuẩn bị đơn hàng">
      <div class="space-y-4 lg:col-span-8">
        <UiSkeleton variant="detail" :lines="4" />
      </div>
      <div class="lg:col-span-4">
        <UiSkeleton variant="card" />
      </div>
    </div>

    <div v-else-if="preview" class="grid items-start gap-6 lg:grid-cols-12">
      <!-- Left: Order Items + Payment Method -->
      <div class="space-y-6 lg:col-span-8">
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <div class="flex items-center justify-between border-b border-border/80 pb-3">
            <h2 class="font-display text-base font-bold text-navy sm:text-lg">
              Khóa học trong đơn ({{ preview.tongSoLuong }})
            </h2>
            <span class="inline-flex items-center gap-1.5 text-xs font-medium text-muted">
              <Clock3 :size="14" class="text-teal" aria-hidden="true" />
              <span>Giữ giá trong {{ preview.thoiHanThanhToanPhut }} phút</span>
            </span>
          </div>

          <ul class="divide-y divide-border/70">
            <li
              v-for="item in preview.items"
              :key="item.maKhoaHoc"
              class="flex items-center justify-between gap-4 py-3.5"
            >
              <div class="flex min-w-0 items-center gap-3">
                <div class="h-14 w-24 shrink-0 overflow-hidden rounded-lg border border-border/70 bg-subtle">
                  <img
                    v-if="item.hinhAnh"
                    :src="resolveMediaUrl(item.hinhAnh)"
                    :alt="item.tieuDe"
                    class="h-full w-full object-cover"
                  >
                  <div v-else class="flex h-full w-full items-center justify-center text-navy/35">
                    <GraduationCap :size="20" aria-hidden="true" />
                  </div>
                </div>
                <div class="min-w-0">
                  <p class="line-clamp-2 text-sm font-semibold text-navy">{{ item.tieuDe }}</p>
                  <p v-if="item.tenNhaCungCap" class="mt-0.5 text-xs text-muted">{{ item.tenNhaCungCap }}</p>
                  <span
                    v-if="item.muaLaiSauHoanTien"
                    class="mt-1 inline-block rounded bg-teal/10 px-2 py-0.5 text-[11px] font-semibold text-teal-dark"
                  >
                    Mua lại — giữ nguyên tiến độ học cũ
                  </span>
                </div>
              </div>
              <p class="shrink-0 text-sm font-bold text-navy tabular-nums">
                {{ formatVnd(item.giaHienTai) }}
              </p>
            </li>
          </ul>
        </section>

        <!-- Payment Method Selection -->
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <h2 class="font-display text-base font-bold text-navy sm:text-lg">Phương thức thanh toán</h2>

          <div v-if="hasAvailablePaymentMethod" class="space-y-3" role="radiogroup" aria-label="Chọn phương thức thanh toán">
            <label
              v-for="method in availablePaymentMethods"
              :key="method.code"
              :class="[
                'flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-[border-color,background-color] duration-150',
                paymentMethod === method.code
                  ? 'border-teal bg-teal/[0.04]'
                  : 'border-border bg-surface hover:border-teal/40',
              ]"
            >
              <input
                v-model="paymentMethod"
                type="radio"
                :value="method.code"
                class="mt-1 size-4 text-teal focus:ring-teal"
              >
              <div class="min-w-0 flex-1 space-y-1">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="text-sm font-semibold text-navy">{{ method.title }}</p>
                  <span class="rounded-full bg-amber/15 px-2 py-0.5 text-[11px] font-semibold text-amber-dark">
                    {{ method.badge }}
                  </span>
                </div>
                <p class="text-xs leading-relaxed text-slate-600">{{ method.description }}</p>
              </div>
            </label>
          </div>

          <div
            v-else
            class="flex items-start gap-3 rounded-xl border border-amber/35 bg-amber/10 p-4 text-xs leading-relaxed text-amber-dark"
            role="status"
          >
            <AlertTriangle :size="16" class="mt-0.5 shrink-0" aria-hidden="true" />
            <div class="space-y-1">
              <p class="font-semibold text-navy">Cổng thanh toán trực tuyến chưa được kích hoạt</p>
              <p class="text-slate-700">
                Hệ thống chính thức hiện chưa kích hoạt cổng thanh toán trực tuyến nên chưa thể hoàn tất giao dịch lúc này. Bạn vẫn có thể lưu khóa học vào Danh sách yêu thích hoặc Giỏ hàng.
              </p>
            </div>
          </div>
        </section>
      </div>

      <!-- Right: Sticky Confirmation Summary -->
      <aside class="lg:sticky lg:top-24 lg:col-span-4">
        <div class="rounded-2xl border border-border bg-surface p-6 space-y-5">
          <h2 class="font-display text-lg font-bold text-navy">Tổng thanh toán</h2>

          <dl class="space-y-3 border-y border-border/80 py-4 text-sm">
            <div class="flex items-center justify-between">
              <dt class="text-slate-600">Số lượng khóa học</dt>
              <dd class="font-semibold text-navy tabular-nums">{{ preview.tongSoLuong }}</dd>
            </div>
            <div class="flex items-center justify-between">
              <dt class="text-slate-600">Hạn thanh toán</dt>
              <dd class="font-semibold text-navy tabular-nums">{{ preview.thoiHanThanhToanPhut }} phút</dd>
            </div>
            <div class="flex items-baseline justify-between pt-2 border-t border-border/60">
              <dt class="font-semibold text-navy">Tổng cộng (VND)</dt>
              <dd class="text-2xl font-bold text-navy tabular-nums">
                {{ formatVnd(preview.tongTien) }}
              </dd>
            </div>
          </dl>

          <button
            type="button"
            class="ui-button ui-button--primary w-full inline-flex items-center justify-center gap-2 active:scale-[0.98]"
            :disabled="submitting || redirectingToGateway || !hasAvailablePaymentMethod || !paymentMethod"
            @click="handleConfirmAndPay"
          >
            <RefreshCw v-if="submitting || redirectingToGateway" :size="16" class="animate-spin" aria-hidden="true" />
            <Lock v-else :size="15" aria-hidden="true" />
            <span>
              {{ !hasAvailablePaymentMethod ? 'Chưa mở cổng thanh toán' : (redirectingToGateway ? 'Đang chuyển hướng sang VNPay Sandbox…' : (submitting ? 'Đang khởi tạo giao dịch…' : 'Xác nhận & Thanh toán')) }}
            </span>
          </button>

          <div class="flex items-center gap-2 text-xs text-muted">
            <ShieldCheck :size="15" class="shrink-0 text-teal" aria-hidden="true" />
            <span>Quyền học chỉ được cấp sau khi Backend xác minh giao dịch thành công.</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
