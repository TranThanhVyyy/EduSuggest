<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  commerceErrorMessage,
  fetchMockPaymentSession,
  formatVnd,
  simulateMockPayment,
} from '@/service/commerceApiService'
import { syncLearnerCommerceState } from '@/service/commerceState'

const route = useRoute()
const router = useRouter()

const txnRef = computed(() => String(route.query.txnRef || '').trim())
const session = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const simulatingOutcome = ref('')

const canSimulate = computed(
  () => Boolean(session.value && session.value.trangThaiThanhToan === 'PENDING' && !session.value.daHetHan),
)

async function loadSession() {
  if (!txnRef.value) {
    errorMessage.value = 'Thiếu mã giao dịch thanh toán mô phỏng.'
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    session.value = await fetchMockPaymentSession(txnRef.value)
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải phiên thanh toán mô phỏng.')
  } finally {
    loading.value = false
  }
}

async function triggerOutcome(ketQua) {
  if (!session.value || simulatingOutcome.value) return
  simulatingOutcome.value = ketQua
  errorMessage.value = ''
  try {
    const res = await simulateMockPayment(session.value.maGiaoDichNoiBo, ketQua)
    if (res.daCapQuyenHoc) {
      await syncLearnerCommerceState({ force: true })
    }
    await router.replace({
      name: 'payment-result',
      query: { orderId: String(res.maDonHang) },
    })
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể xử lý kết quả thanh toán mô phỏng.')
  } finally {
    simulatingOutcome.value = ''
  }
}

onMounted(() => {
  loadSession()
})
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <!-- Mandatory Sandbox Banner -->
    <div class="flex items-start gap-3 rounded-xl border border-amber/40 bg-amber/10 px-4 py-3.5 text-sm text-amber-dark">
      <ShieldAlert :size="18" class="mt-0.5 shrink-0" aria-hidden="true" />
      <div>
        <p class="font-bold">Thanh toán mô phỏng – Không phát sinh giao dịch tiền thật</p>
        <p class="mt-0.5 text-xs">
          Trang mô phỏng cổng thanh toán dành riêng cho môi trường kiểm thử. Chữ ký giao dịch được xác minh hoàn toàn tại Backend.
        </p>
      </div>
    </div>

    <UiAlert
      v-if="errorMessage"
      variant="danger"
      title="Không thể thực hiện giao dịch mô phỏng"
      :message="errorMessage"
    >
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm mt-3 inline-flex items-center gap-1.5"
        @click="loadSession"
      >
        <RefreshCw :size="13" aria-hidden="true" />
        <span>Tải lại</span>
      </button>
    </UiAlert>

    <UiSkeleton v-if="loading" variant="detail" :lines="5" />

    <section v-else-if="session" class="rounded-2xl border border-border bg-surface p-6 space-y-6">
      <div class="flex flex-wrap items-start justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <p class="text-xs font-semibold text-muted">Mã đơn hàng</p>
          <h1 class="mt-0.5 font-display text-xl font-bold text-navy tabular-nums">
            {{ session.maSoDonHang }}
          </h1>
          <p class="mt-1 text-xs text-muted tabular-nums">
            Mã giao dịch: {{ session.maGiaoDichNoiBo }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-xs font-semibold text-muted">Số tiền thanh toán</p>
          <p class="mt-0.5 text-2xl font-bold text-navy tabular-nums">
            {{ formatVnd(session.soTien) }}
          </p>
        </div>
      </div>

      <!-- Snapshot Course List -->
      <div class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-wider text-muted">Chi tiết khóa học</p>
        <ul class="divide-y divide-border/70 rounded-xl border border-border/80 bg-canvas/50 px-4">
          <li
            v-for="item in session.items"
            :key="item.maChiTietDonHang"
            class="flex items-center justify-between gap-3 py-2.5 text-sm"
          >
            <span class="min-w-0 truncate font-medium text-navy">{{ item.tieuDeSnapshot }}</span>
            <span class="shrink-0 font-semibold text-navy tabular-nums">
              {{ formatVnd(item.giaTaiThoiDiemMua) }}
            </span>
          </li>
        </ul>
      </div>

      <!-- Already finalized or expired -->
      <div
        v-if="!canSimulate"
        class="flex flex-col gap-3 rounded-xl border border-border bg-subtle/60 p-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="flex items-center gap-2 text-sm text-navy">
          <AlertTriangle :size="16" class="text-amber shrink-0" aria-hidden="true" />
          <span>
            Phiên giao dịch hiện ở trạng thái <strong>{{ session.trangThaiThanhToan }}</strong> (Đơn: <strong>{{ session.trangThaiDonHang }}</strong>).
          </span>
        </div>
        <RouterLink
          :to="{ name: 'payment-result', query: { orderId: String(session.maDonHang) } }"
          class="ui-button ui-button--primary ui-button--sm shrink-0"
        >
          Xem kết quả đơn hàng
        </RouterLink>
      </div>

      <!-- 4 Sandbox Outcome Controls -->
      <div v-else class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-wider text-muted">
          Chọn kịch bản kết quả để kiểm thử
        </p>

        <div class="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            class="flex items-center justify-center gap-2 rounded-xl bg-teal px-4 py-3 text-sm font-semibold text-white transition-[background-color,transform] duration-150 hover:bg-teal-dark active:scale-[0.97] disabled:opacity-60"
            :disabled="Boolean(simulatingOutcome)"
            @click="triggerOutcome('PAID')"
          >
            <RefreshCw v-if="simulatingOutcome === 'PAID'" :size="16" class="animate-spin" aria-hidden="true" />
            <CheckCircle2 v-else :size="16" aria-hidden="true" />
            <span>Thanh toán thành công</span>
          </button>

          <button
            type="button"
            class="flex items-center justify-center gap-2 rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 transition-[background-color,transform] duration-150 hover:bg-rose-100 active:scale-[0.97] disabled:opacity-60"
            :disabled="Boolean(simulatingOutcome)"
            @click="triggerOutcome('FAILED')"
          >
            <RefreshCw v-if="simulatingOutcome === 'FAILED'" :size="16" class="animate-spin" aria-hidden="true" />
            <XCircle v-else :size="16" aria-hidden="true" />
            <span>Thanh toán thất bại</span>
          </button>

          <button
            type="button"
            class="flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-sm font-semibold text-navy transition-[background-color,transform] duration-150 hover:bg-subtle active:scale-[0.97] disabled:opacity-60"
            :disabled="Boolean(simulatingOutcome)"
            @click="triggerOutcome('CANCELLED')"
          >
            <RefreshCw v-if="simulatingOutcome === 'CANCELLED'" :size="16" class="animate-spin" aria-hidden="true" />
            <Ban v-else :size="16" aria-hidden="true" />
            <span>Hủy giao dịch</span>
          </button>

          <button
            type="button"
            class="flex items-center justify-center gap-2 rounded-xl border border-amber/40 bg-amber/10 px-4 py-3 text-sm font-semibold text-amber-dark transition-[background-color,transform] duration-150 hover:bg-amber/20 active:scale-[0.97] disabled:opacity-60"
            :disabled="Boolean(simulatingOutcome)"
            @click="triggerOutcome('EXPIRED')"
          >
            <RefreshCw v-if="simulatingOutcome === 'EXPIRED'" :size="16" class="animate-spin" aria-hidden="true" />
            <Clock3 v-else :size="16" aria-hidden="true" />
            <span>Mô phỏng hết hạn</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
