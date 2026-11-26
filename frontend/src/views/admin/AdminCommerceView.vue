<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ReceiptText,
  RefreshCw,
  ShieldAlert,
} from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  adminActivateReconciliation,
  adminCreateExceptionRefund,
  adminExecuteExceptionRefund,
  adminVerifyExceptionRefund,
  commerceErrorMessage,
  fetchAdminCommerceOverview,
  fetchAdminIncidents,
  fetchAdminOrders,
  fetchAdminReconciliationQueue,
  fetchAdminRevenueDashboard,
  formatVnd,
  generateIdempotencyKey,
} from '@/service/commerceApiService'

const activeTab = ref('revenue')
const loading = ref(true)
const errorMessage = ref('')
const actionMessage = ref('')
const busyPaymentId = ref(null)

const overview = ref(null)
const revenue = ref(null)
const ordersData = ref({ items: [], total: 0, page: 1, totalPages: 0 })
const orderStatusFilter = ref('')
const orderSearch = ref('')
const reconciliationItems = ref([])
const incidents = ref([])

const maxDailyRevenue = computed(() => {
  const list = revenue.value?.chuoiDoanhThuTheoNgay || []
  return Math.max(1, ...list.map((d) => Number(d.doanhThuThuan || 0)))
})

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

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [ov, rev, ords, rec, inc] = await Promise.all([
      fetchAdminCommerceOverview(),
      fetchAdminRevenueDashboard(),
      fetchAdminOrders({ page: 1, pageSize: 20, trangThai: orderStatusFilter.value, q: orderSearch.value }),
      fetchAdminReconciliationQueue(),
      fetchAdminIncidents(),
    ])
    overview.value = ov
    revenue.value = rev
    ordersData.value = ords
    reconciliationItems.value = rec || []
    incidents.value = inc || []
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải dữ liệu thương mại ADMIN.')
  } finally {
    loading.value = false
  }
}

async function handleActivateEntitlement(txn) {
  if (busyPaymentId.value) return
  busyPaymentId.value = txn.maThanhToan
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    await adminActivateReconciliation(txn.maThanhToan, 'ADMIN xác minh chứng từ thu tiền hợp lệ và khôi phục quyền học.')
    actionMessage.value = `Đã khôi phục quyền học thành công cho đơn ${txn.maSoDonHang}.`
    await loadAll()
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể khôi phục quyền học cho giao dịch này.')
  } finally {
    busyPaymentId.value = null
  }
}

async function handleExceptionRefundStep(txn) {
  if (busyPaymentId.value) return
  busyPaymentId.value = txn.maThanhToan
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    if (!txn.trangThaiHoanTien) {
      const scope = txn.trangThai === 'PAID' ? 'FULL_ORDER' : 'EXCESS_PAYMENT'
      await adminCreateExceptionRefund(
        {
          maDonHang: txn.maDonHang,
          maThanhToan: txn.maThanhToan,
          soTienHoan: String(txn.soTienDaThuThucTe || txn.soTien),
          loaiSuCo: scope === 'EXCESS_PAYMENT' ? 'DUPLICATE_CHARGE' : 'CANNOT_PROVISION_COURSE',
          phamViHoan: scope,
          lyDo: `Hoàn tiền ngoại lệ cho sự cố giao dịch ${txn.maGiaoDichNoiBo}.`,
        },
        generateIdempotencyKey(`ref-${txn.maThanhToan}`),
      )
      actionMessage.value = `Đã tạo yêu cầu hoàn tiền ngoại lệ (PENDING_REVIEW) cho giao dịch ${txn.maGiaoDichNoiBo}.`
    } else if (txn.trangThaiHoanTien === 'PENDING_REVIEW') {
      await adminVerifyExceptionRefund(txn.maThanhToan, 'ADMIN đã xác minh bằng chứng thu tiền từ cổng thanh toán.')
      actionMessage.value = `Đã xác minh hoàn tiền (VERIFIED) cho giao dịch ${txn.maGiaoDichNoiBo}.`
    } else if (['VERIFIED', 'REFUND_FAILED'].includes(txn.trangThaiHoanTien)) {
      const res = await adminExecuteExceptionRefund(txn.maThanhToan, 'REFUNDED')
      actionMessage.value = `Hoàn tiền ${res.refundId} hoàn tất với trạng thái ${res.trangThai}.`
    }
    await loadAll()
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể xử lý bước hoàn tiền ngoại lệ.')
  } finally {
    busyPaymentId.value = null
  }
}

onMounted(() => {
  loadAll()
})
</script>

<template>
  <div class="space-y-8">
    <header class="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1.5">
        <h1 class="ui-page-title text-navy">Quản lý Thương mại &amp; Doanh thu</h1>
        <p class="text-sm text-slate-600">
          Theo dõi doanh thu hợp lệ, đơn hàng, đối soát thanh toán bất thường và xử lý hoàn tiền ngoại lệ.
        </p>
      </div>
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5 active:scale-[0.97]"
        :disabled="loading"
        @click="loadAll"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <UiAlert v-if="actionMessage" variant="success" :message="actionMessage" />
    <UiAlert v-if="errorMessage" variant="danger" title="Lỗi thao tác" :message="errorMessage" />

    <!-- KPI Ledger -->
    <div v-if="loading && !overview" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UiSkeleton v-for="i in 4" :key="i" variant="card" />
    </div>

    <section v-else-if="overview" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <article class="rounded-2xl border border-border bg-surface p-5">
        <p class="text-xs font-semibold text-muted">Doanh thu thuần hợp lệ</p>
        <p class="mt-2 text-2xl font-bold text-navy tabular-nums">{{ formatVnd(overview.doanhThuThuanHopLe) }}</p>
        <p class="mt-1 text-xs text-slate-600 tabular-nums">
          Ghi nhận: {{ formatVnd(overview.doanhThuGhiNhan) }} · Hoàn sự cố: {{ formatVnd(overview.hoanTienSuCo) }}
        </p>
      </article>
      <article class="rounded-2xl border border-border bg-surface p-5">
        <p class="text-xs font-semibold text-muted">Đơn hàng thành công</p>
        <p class="mt-2 text-2xl font-bold text-teal-dark tabular-nums">{{ overview.donThanhCong }}</p>
        <p class="mt-1 text-xs text-slate-600 tabular-nums">
          AOV: {{ formatVnd(overview.giaTriDonTrungBinh) }} · Chờ xử lý: {{ overview.donChuaHoanTat }}
        </p>
      </article>
      <article class="rounded-2xl border border-border bg-surface p-5">
        <p class="text-xs font-semibold text-muted">Đối soát &amp; Tiền thu dư</p>
        <p class="mt-2 text-2xl font-bold text-amber-dark tabular-nums">{{ overview.giaoDichCanDoiSoat }}</p>
        <p class="mt-1 text-xs text-slate-600 tabular-nums">
          Thu dư chờ hoàn: {{ formatVnd(overview.tienThuDuChoHoan) }}
        </p>
      </article>
      <article class="rounded-2xl border border-border bg-surface p-5">
        <p class="text-xs font-semibold text-muted">Sự cố &amp; Hoàn tiền ngoại lệ</p>
        <p class="mt-2 text-2xl font-bold text-navy tabular-nums">{{ overview.suCoChuaXuLy }} sự cố</p>
        <p class="mt-1 text-xs text-slate-600 tabular-nums">
          Đã hoàn xác nhận: {{ formatVnd(overview.tienDaHoanXacNhan) }}
        </p>
      </article>
    </section>

    <!-- Workspace Tabs -->
    <div class="flex flex-wrap items-center gap-2 border-b border-border/80 pb-3" role="tablist">
      <button
        v-for="tab in [
          { id: 'revenue', label: 'Doanh thu & Phân tích', icon: BarChart3 },
          { id: 'orders', label: `Đơn hàng (${ordersData.total})`, icon: ReceiptText },
          { id: 'reconciliation', label: `Đối soát & Hoàn tiền (${reconciliationItems.length})`, icon: ShieldAlert },
          { id: 'incidents', label: `Báo cáo sự cố (${incidents.length})`, icon: AlertTriangle },
        ]"
        :key="tab.id"
        type="button"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :class="[
          'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-colors active:scale-[0.97]',
          activeTab === tab.id
            ? 'bg-navy text-white'
            : 'border border-border bg-surface text-slate-600 hover:border-teal/40 hover:text-navy',
        ]"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" :size="14" aria-hidden="true" />
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- TAB 1: Revenue Dashboard -->
    <div v-if="activeTab === 'revenue' && revenue" class="grid gap-6 lg:grid-cols-12">
      <section class="rounded-2xl border border-border bg-surface p-6 space-y-4 lg:col-span-7">
        <h2 class="font-display text-base font-bold text-navy">Doanh thu thuần theo ngày</h2>
        <p class="text-xs text-muted">{{ revenue.ghiChuChinhSach }}</p>
        <div v-if="!revenue.chuoiDoanhThuTheoNgay.length" class="py-6 text-sm text-muted">
          Chưa có giao dịch thanh toán thành công nào để vẽ biểu đồ.
        </div>
        <ul v-else class="space-y-3">
          <li v-for="pt in revenue.chuoiDoanhThuTheoNgay" :key="pt.ngay" class="space-y-1">
            <div class="flex items-center justify-between text-xs">
              <span class="font-medium text-navy tabular-nums">{{ pt.ngay }}</span>
              <span class="font-semibold text-navy tabular-nums">
                {{ formatVnd(pt.doanhThuThuan) }} ({{ pt.soDonThanhCong }} đơn)
              </span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
              <div
                class="h-full rounded-full bg-teal"
                :style="{ width: `${Math.max(4, Math.round((Number(pt.doanhThuThuan) / maxDailyRevenue) * 100))}%` }"
              />
            </div>
          </li>
        </ul>
      </section>

      <section class="rounded-2xl border border-border bg-surface p-6 space-y-4 lg:col-span-5">
        <h2 class="font-display text-base font-bold text-navy">Top khóa học bán chạy</h2>
        <p v-if="!revenue.topKhoaHoc.length" class="py-6 text-sm text-muted">
          Chưa có khóa học nào phát sinh doanh thu.
        </p>
        <ul v-else class="divide-y divide-border/70">
          <li v-for="c in revenue.topKhoaHoc" :key="c.maKhoaHoc" class="flex items-center justify-between gap-3 py-3 text-sm">
            <div class="min-w-0">
              <p class="truncate font-semibold text-navy">{{ c.tieuDe }}</p>
              <p class="text-xs text-muted tabular-nums">{{ c.soLuotBan }} lượt bán</p>
            </div>
            <span class="shrink-0 font-bold text-navy tabular-nums">{{ formatVnd(c.doanhThuThuan) }}</span>
          </li>
        </ul>
      </section>
    </div>

    <!-- TAB 2: Orders Table -->
    <section v-else-if="activeTab === 'orders'" class="rounded-2xl border border-border bg-surface p-6 space-y-4">
      <div class="flex flex-wrap items-center gap-3">
        <input
          v-model="orderSearch"
          type="search"
          placeholder="Tìm theo mã đơn hàng hoặc người mua…"
          class="h-9 min-w-[220px] flex-1 rounded-lg border border-border bg-subtle/60 px-3 text-sm text-navy outline-none focus:border-teal focus:bg-surface"
          @keyup.enter="loadAll"
        >
        <select
          v-model="orderStatusFilter"
          class="h-9 rounded-lg border border-border bg-surface px-3 text-xs font-semibold text-navy outline-none"
          @change="loadAll"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="PAID">PAID</option>
          <option value="PENDING">PENDING</option>
          <option value="FAILED">FAILED</option>
          <option value="CANCELLED">CANCELLED</option>
          <option value="EXPIRED">EXPIRED</option>
          <option value="REFUNDED">REFUNDED</option>
        </select>
      </div>

      <UiEmptyState
        v-if="!ordersData.items.length"
        :icon="ReceiptText"
        title="Không có đơn hàng phù hợp"
        description="Các đơn hàng phát sinh trên Marketplace sẽ hiển thị tại đây."
      />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-xs sm:text-sm">
          <thead>
            <tr class="border-b border-border text-xs text-muted">
              <th class="pb-2.5 pr-4 font-semibold">Mã đơn</th>
              <th class="pb-2.5 pr-4 font-semibold">Người mua</th>
              <th class="pb-2.5 pr-4 font-semibold">Tổng tiền</th>
              <th class="pb-2.5 pr-4 font-semibold">Trạng thái</th>
              <th class="pb-2.5 font-semibold">Ngày tạo</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/70">
            <tr v-for="o in ordersData.items" :key="o.maDonHang">
              <td class="py-3 pr-4 font-semibold text-navy tabular-nums">{{ o.maSoDonHang }}</td>
              <td class="py-3 pr-4 text-slate-700">{{ o.tenNguoiMua || `User #${o.maNguoiDung}` }}</td>
              <td class="py-3 pr-4 font-bold text-navy tabular-nums">{{ formatVnd(o.tongTien) }}</td>
              <td class="py-3 pr-4">
                <span class="font-semibold text-navy">{{ o.trangThai }}</span>
                <span v-if="o.canDoiSoat" class="ml-1.5 rounded bg-amber/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber-dark">Đối soát</span>
              </td>
              <td class="py-3 text-muted tabular-nums">{{ formatDateTime(o.ngayTao) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- TAB 3: Reconciliation & Exception Refund Workspace -->
    <section v-else-if="activeTab === 'reconciliation'" class="rounded-2xl border border-border bg-surface p-6 space-y-4">
      <UiEmptyState
        v-if="!reconciliationItems.length"
        :icon="CheckCircle2"
        title="Không có giao dịch cần đối soát"
        description="Mọi giao dịch thanh toán hiện đều nhất quán và không có khoản thu dư chờ xử lý."
      />
      <ul v-else class="space-y-4">
        <li
          v-for="txn in reconciliationItems"
          :key="txn.maThanhToan"
          class="rounded-xl border border-border p-4 space-y-3"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="space-y-1">
              <p class="text-sm font-bold text-navy tabular-nums">
                {{ txn.maSoDonHang }} · {{ txn.maGiaoDichNoiBo }}
              </p>
              <p class="text-xs text-slate-600">
                Cổng: <strong>{{ txn.congThanhToan }}</strong> · Thu thực tế: <strong class="tabular-nums">{{ formatVnd(txn.soTienDaThuThucTe) }}</strong> · Lý do: {{ txn.lyDoDoiSoat || 'Cần kiểm tra' }}
              </p>
              <p v-if="txn.trangThaiHoanTien" class="text-xs font-semibold text-teal-dark">
                Trạng thái hoàn tiền ngoại lệ: {{ txn.trangThaiHoanTien }}
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                v-if="txn.canDoiSoat && txn.daThuTien && !txn.trangThaiHoanTien"
                type="button"
                class="ui-button ui-button--outline ui-button--sm active:scale-[0.97]"
                :disabled="busyPaymentId === txn.maThanhToan"
                @click="handleActivateEntitlement(txn)"
              >
                Khôi phục quyền học
              </button>
              <button
                v-if="txn.daThuTien && txn.trangThaiHoanTien !== 'REFUNDED' && txn.trangThaiHoanTien !== 'UNKNOWN'"
                type="button"
                class="ui-button ui-button--primary ui-button--sm active:scale-[0.97]"
                :disabled="busyPaymentId === txn.maThanhToan"
                @click="handleExceptionRefundStep(txn)"
              >
                <template v-if="!txn.trangThaiHoanTien">Tạo hoàn tiền ngoại lệ</template>
                <template v-else-if="txn.trangThaiHoanTien === 'PENDING_REVIEW'">Xác minh hoàn tiền</template>
                <template v-else>Thực thi hoàn tiền</template>
              </button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- TAB 4: User Payment Incidents -->
    <section v-else-if="activeTab === 'incidents'" class="rounded-2xl border border-border bg-surface p-6 space-y-4">
      <UiEmptyState
        v-if="!incidents.length"
        :icon="AlertTriangle"
        title="Chưa có báo cáo sự cố thanh toán nào"
        description="Khi người học gửi báo cáo sự cố từ Chi tiết đơn hàng, hồ sơ sẽ xuất hiện tại đây."
      />
      <ul v-else class="divide-y divide-border/70">
        <li v-for="inc in incidents" :key="inc.maSuCo" class="py-3.5 space-y-1">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <p class="text-sm font-bold text-navy tabular-nums">{{ inc.maSuCo }} · {{ inc.maSoDonHang }}</p>
            <span class="rounded-full bg-amber/15 px-2.5 py-0.5 text-[11px] font-semibold text-amber-dark">
              {{ inc.loaiSuCo }} · {{ inc.trangThai }}
            </span>
          </div>
          <p class="text-sm text-slate-700">{{ inc.moTa }}</p>
          <p class="text-xs text-muted tabular-nums">Người báo cáo #{{ inc.maNguoiBaoCao }} · {{ formatDateTime(inc.ngayBaoCao) }}</p>
        </li>
      </ul>
    </section>
  </div>
</template>
