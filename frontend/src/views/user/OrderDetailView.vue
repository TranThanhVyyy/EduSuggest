<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Clock3,
  PlayCircle,
  RefreshCw,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  cancelOrder,
  commerceErrorMessage,
  fetchOrderDetail,
  formatVnd,
  generateIdempotencyKey,
  initiatePayment,
  reportPaymentIncident,
} from '@/service/commerceApiService'
import { commerceState, showCommerceToast } from '@/service/commerceState'

const route = useRoute()
const router = useRouter()

const order = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const cancelling = ref(false)
const confirmCancelOpen = ref(false)
const paying = ref(false)

const incidentOpen = ref(false)
const incidentType = ref('CHARGED_NO_ACCESS')
const incidentDesc = ref('')
const reportingIncident = ref(false)
const incidentSubmitted = ref('')

const INCIDENT_TYPES = [
  { value: 'CHARGED_NO_ACCESS', label: 'Đã trừ tiền nhưng chưa vào học được' },
  { value: 'DUPLICATE_CHARGE', label: 'Bị trừ tiền nhiều lần cho cùng đơn hàng' },
  { value: 'WRONG_AMOUNT', label: 'Số tiền bị trừ không đúng học phí' },
  { value: 'CANCELLED_OR_EXPIRED_CHARGED', label: 'Đơn đã hủy/hết hạn nhưng vẫn bị trừ tiền' },
  { value: 'OTHER_PAYMENT_ERROR', label: 'Sự cố thanh toán khác' },
]

async function handleReportIncident() {
  if (!order.value || reportingIncident.value || incidentDesc.value.trim().length < 10) return
  reportingIncident.value = true
  errorMessage.value = ''
  try {
    const res = await reportPaymentIncident(order.value.maDonHang, {
      loaiSuCo: incidentType.value,
      moTa: incidentDesc.value.trim(),
    })
    incidentSubmitted.value = `Đã ghi nhận báo cáo sự cố ${res.maSuCo}. Quản trị viên sẽ kiểm tra và đối soát giao dịch cho bạn.`
    incidentDesc.value = ''
    incidentOpen.value = false
    await loadOrder()
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể gửi báo cáo sự cố thanh toán.')
  } finally {
    reportingIncident.value = false
  }
}

const STATUS_LABELS = {
  PAID: 'Đã thanh toán',
  PENDING: 'Chờ thanh toán',
  FAILED: 'Thất bại',
  CANCELLED: 'Đã hủy',
  EXPIRED: 'Hết hạn',
  REFUNDED: 'Đã hoàn tiền',
}

const canResumePayment = computed(() => {
  if (!order.value || !commerceState.mockPaymentEnabled) return false
  if (!['PENDING', 'FAILED'].includes(order.value.trangThai)) return false
  const expiry = new Date(order.value.hanThanhToan)
  return !Number.isNaN(expiry.getTime()) && expiry.getTime() > Date.now()
})

const canCancel = computed(() =>
  Boolean(order.value && ['PENDING', 'FAILED'].includes(order.value.trangThai) && canResumePayment.value),
)

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

async function loadOrder() {
  loading.value = true
  errorMessage.value = ''
  try {
    order.value = await fetchOrderDetail(route.params.id)
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải chi tiết đơn hàng.')
  } finally {
    loading.value = false
  }
}

async function handleCancel() {
  if (!order.value || cancelling.value) return
  cancelling.value = true
  errorMessage.value = ''
  try {
    order.value = await cancelOrder(order.value.maDonHang, 'Người học chủ động hủy đơn hàng.')
    confirmCancelOpen.value = false
    showCommerceToast('Đơn hàng đã được hủy.', 'info')
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể hủy đơn hàng.')
  } finally {
    cancelling.value = false
  }
}

async function handleContinuePayment() {
  if (!order.value || paying.value) return
  paying.value = true
  errorMessage.value = ''
  try {
    const payment = await initiatePayment(
      order.value.maDonHang,
      'MOCK_SANDBOX',
      generateIdempotencyKey('detail-pay'),
    )
    await router.push({
      name: 'mock-payment',
      query: { txnRef: payment.maGiaoDichNoiBo, orderId: String(order.value.maDonHang) },
    })
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tiếp tục thanh toán.')
  } finally {
    paying.value = false
  }
}

onMounted(() => {
  loadOrder()
})
</script>

<template>
  <div class="space-y-8">
    <div class="space-y-2 border-b border-border/80 pb-6">
      <RouterLink
        :to="{ name: 'order-history' }"
        class="inline-flex items-center gap-1.5 text-xs font-semibold text-teal hover:underline"
      >
        <ArrowLeft :size="14" aria-hidden="true" />
        <span>Quay lại lịch sử mua hàng</span>
      </RouterLink>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="ui-page-title text-navy tabular-nums">
            {{ order?.maSoDonHang || 'Chi tiết đơn hàng' }}
          </h1>
          <p v-if="order" class="mt-1 text-sm text-slate-600 tabular-nums">
            Tạo lúc {{ formatDateTime(order.ngayTao) }} · Trạng thái: <strong class="text-navy">{{ STATUS_LABELS[order.trangThai] || order.trangThai }}</strong>
          </p>
        </div>

        <div v-if="order" class="flex flex-wrap items-center gap-2">
          <button
            v-if="canResumePayment"
            type="button"
            class="ui-button ui-button--primary ui-button--sm active:scale-[0.97]"
            :disabled="paying"
            @click="handleContinuePayment"
          >
            {{ paying ? 'Đang chuyển…' : 'Tiếp tục thanh toán' }}
          </button>
          <button
            v-if="canCancel && !confirmCancelOpen"
            type="button"
            class="ui-button ui-button--outline ui-button--sm text-rose-700 hover:border-rose-300 hover:bg-rose-50 active:scale-[0.97]"
            @click="confirmCancelOpen = true"
          >
            Hủy đơn hàng
          </button>
        </div>
      </div>
    </div>

    <!-- Inline Cancel Confirmation -->
    <div
      v-if="confirmCancelOpen"
      class="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50/70 p-4 sm:flex-row sm:items-center sm:justify-between"
      role="alert"
    >
      <p class="text-sm font-medium text-rose-900">
        Xác nhận hủy đơn hàng {{ order?.maSoDonHang }}? Đơn hàng đã hủy không thể thanh toán lại.
      </p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="ui-button ui-button--outline ui-button--sm bg-surface"
          :disabled="cancelling"
          @click="confirmCancelOpen = false"
        >
          Quay lại
        </button>
        <button
          type="button"
          class="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 active:scale-[0.97]"
          :disabled="cancelling"
          @click="handleCancel"
        >
          {{ cancelling ? 'Đang hủy…' : 'Xác nhận hủy' }}
        </button>
      </div>
    </div>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể tải chi tiết đơn hàng"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadOrder"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Thử lại</span>
      </button>
    </UiAlert>

    <UiSkeleton v-if="loading" variant="detail" :lines="6" />

    <div v-else-if="order" class="grid gap-6 lg:grid-cols-12">
      <!-- Left: Courses + Payment Attempts -->
      <div class="space-y-6 lg:col-span-8">
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <h2 class="font-display text-base font-bold text-navy sm:text-lg">
            Khóa học trong đơn ({{ order.items.length }})
          </h2>

          <ul class="divide-y divide-border/70">
            <li
              v-for="item in order.items"
              :key="item.maChiTietDonHang"
              class="flex flex-wrap items-center justify-between gap-3 py-3.5"
            >
              <div class="min-w-0">
                <RouterLink
                  :to="{ name: 'course-detail', params: { id: item.maKhoaHoc } }"
                  class="text-sm font-semibold text-navy hover:text-teal"
                >
                  {{ item.tieuDeSnapshot }}
                </RouterLink>
                <p class="mt-0.5 text-xs text-muted tabular-nums">
                  Giá snapshot: {{ formatVnd(item.giaTaiThoiDiemMua) }}
                </p>
              </div>
              <RouterLink
                v-if="order.trangThai === 'PAID'"
                :to="{ name: 'learning', params: { courseId: item.maKhoaHoc } }"
                class="ui-button ui-button--primary ui-button--sm inline-flex items-center gap-1.5 active:scale-[0.97]"
              >
                <PlayCircle :size="14" aria-hidden="true" />
                <span>Vào học</span>
              </RouterLink>
            </li>
          </ul>
        </section>

        <!-- Payment Attempts History (Safe Fields Only) -->
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <h2 class="font-display text-base font-bold text-navy sm:text-lg">
            Lịch sử lần thử thanh toán ({{ order.thanhToans.length }})
          </h2>

          <p v-if="!order.thanhToans.length" class="text-sm text-muted">
            Chưa có giao dịch thanh toán nào được khởi tạo cho đơn hàng này.
          </p>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left text-xs sm:text-sm">
              <thead>
                <tr class="border-b border-border text-xs text-muted">
                  <th class="pb-2.5 pr-4 font-semibold">Mã giao dịch</th>
                  <th class="pb-2.5 pr-4 font-semibold">Cổng</th>
                  <th class="pb-2.5 pr-4 font-semibold">Số tiền</th>
                  <th class="pb-2.5 pr-4 font-semibold">Trạng thái</th>
                  <th class="pb-2.5 font-semibold">Thời gian</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/70">
                <tr v-for="p in order.thanhToans" :key="p.maThanhToan">
                  <td class="py-3 pr-4 font-medium text-navy tabular-nums">{{ p.maGiaoDichNoiBo }}</td>
                  <td class="py-3 pr-4 text-slate-600">
                    {{ p.laThanhToanMoPhong ? 'Mock Sandbox' : p.congThanhToan }}
                  </td>
                  <td class="py-3 pr-4 font-semibold text-navy tabular-nums">{{ formatVnd(p.soTien) }}</td>
                  <td class="py-3 pr-4">
                    <span class="font-semibold text-navy">{{ STATUS_LABELS[p.trangThai] || p.trangThai }}</span>
                    <span v-if="p.canDoiSoat" class="ml-1.5 rounded bg-amber/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber-dark">
                      Cần đối soát
                    </span>
                  </td>
                  <td class="py-3 text-muted tabular-nums">{{ formatDateTime(p.ngayThanhToan || p.ngayTao) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- Right: Order Metadata Card -->
      <aside class="lg:col-span-4">
        <div class="rounded-2xl border border-border bg-surface p-6 space-y-4">
          <h2 class="font-display text-base font-bold text-navy">Thông tin thanh toán</h2>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between gap-2">
              <dt class="text-muted">Nguồn tạo</dt>
              <dd class="font-medium text-navy">{{ order.nguonTao === 'BUY_NOW' ? 'Mua ngay' : 'Giỏ hàng' }}</dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-muted">Hạn thanh toán</dt>
              <dd class="font-medium text-navy tabular-nums">{{ formatDateTime(order.hanThanhToan) }}</dd>
            </div>
            <div v-if="order.ngayThanhToan" class="flex justify-between gap-2">
              <dt class="text-muted">Ngày thanh toán</dt>
              <dd class="font-medium text-teal-dark tabular-nums">{{ formatDateTime(order.ngayThanhToan) }}</dd>
            </div>
            <div v-if="order.lyDoHuyHoacHoan" class="border-t border-border/70 pt-3">
              <dt class="text-xs text-muted">Ghi chú</dt>
              <dd class="mt-1 text-xs text-slate-700">{{ order.lyDoHuyHoacHoan }}</dd>
            </div>
            <div class="flex items-baseline justify-between border-t border-border/80 pt-3">
              <dt class="font-semibold text-navy">Tổng tiền</dt>
              <dd class="text-xl font-bold text-navy tabular-nums">{{ formatVnd(order.tongTien) }}</dd>
            </div>
          </dl>
          <p v-if="canResumePayment" class="flex items-center gap-1.5 text-xs text-amber-dark">
            <Clock3 :size="14" aria-hidden="true" />
            <span>Đơn hàng vẫn còn trong thời hạn thanh toán.</span>
          </p>

          <!-- User Payment Incident Report (Never shows general refund button) -->
          <div v-if="order.thanhToans?.length" class="border-t border-border/80 pt-4 space-y-3">
            <p v-if="incidentSubmitted" class="rounded-lg bg-teal/10 p-3 text-xs font-medium text-teal-dark">
              {{ incidentSubmitted }}
            </p>
            <button
              v-if="!incidentOpen"
              type="button"
              class="ui-button ui-button--outline ui-button--sm w-full active:scale-[0.98]"
              @click="incidentOpen = true"
            >
              Báo cáo sự cố thanh toán
            </button>

            <form v-else class="space-y-3" @submit.prevent="handleReportIncident">
              <p class="text-xs font-semibold text-navy">Báo cáo sự cố thanh toán</p>
              <select
                v-model="incidentType"
                aria-label="Loại sự cố thanh toán"
                class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-navy outline-none focus:border-teal"
              >
                <option v-for="t in INCIDENT_TYPES" :key="t.value" :value="t.value">
                  {{ t.label }}
                </option>
              </select>
              <textarea
                v-model="incidentDesc"
                rows="3"
                required
                minlength="10"
                maxlength="1000"
                placeholder="Mô tả sự cố bạn gặp phải (không nhập mật khẩu ngân hàng, OTP hoặc số thẻ)."
                class="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-navy outline-none focus:border-teal"
              />
              <p class="text-[11px] text-muted">
                Tuyệt đối không cung cấp mật khẩu ngân hàng, mã OTP hoặc số thẻ thanh toán.
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="ui-button ui-button--outline ui-button--sm flex-1"
                  @click="incidentOpen = false"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  class="ui-button ui-button--primary ui-button--sm flex-1"
                  :disabled="reportingIncident || incidentDesc.trim().length < 10"
                >
                  {{ reportingIncident ? 'Đang gửi…' : 'Gửi báo cáo' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
