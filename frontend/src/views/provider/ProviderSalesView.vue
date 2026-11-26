<script setup>
import { computed, onMounted, ref } from 'vue'
import { BarChart3, ReceiptText, RefreshCw } from 'lucide-vue-next'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import {
  commerceErrorMessage,
  fetchProviderSalesItems,
  fetchProviderSalesSummary,
  formatVnd,
} from '@/service/commerceApiService'

const summary = ref(null)
const items = ref([])
const loading = ref(true)
const errorMessage = ref('')

const maxDaily = computed(() => {
  const list = summary.value?.chuoiDoanhThuTheoNgay || []
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

async function loadSales() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [sum, list] = await Promise.all([
      fetchProviderSalesSummary(),
      fetchProviderSalesItems(),
    ])
    summary.value = sum
    items.value = list || []
  } catch (error) {
    errorMessage.value = commerceErrorMessage(error, 'Không thể tải báo cáo doanh thu bán hàng.')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSales()
})
</script>

<template>
  <div class="space-y-8">
    <header class="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1.5">
        <h1 class="ui-page-title text-navy">Doanh thu &amp; Bán hàng</h1>
        <p class="text-sm text-slate-600">
          Theo dõi doanh thu ghi nhận và lượt mua cho các khóa học thuộc sở hữu của bạn.
        </p>
      </div>
      <button
        type="button"
        class="ui-button ui-button--outline ui-button--sm inline-flex items-center gap-1.5 active:scale-[0.97]"
        :disabled="loading"
        @click="loadSales"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" aria-hidden="true" />
        <span>Làm mới</span>
      </button>
    </header>

    <UiAlert v-if="errorMessage" variant="danger" title="Không thể tải dữ liệu" :message="errorMessage" />

    <div v-if="loading && !summary" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UiSkeleton v-for="i in 4" :key="i" variant="card" />
    </div>

    <template v-else-if="summary">
      <section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article class="rounded-2xl border border-border bg-surface p-5">
          <p class="text-xs font-semibold text-muted">Doanh thu thuần</p>
          <p class="mt-2 text-2xl font-bold text-navy tabular-nums">{{ formatVnd(summary.doanhThuThuan) }}</p>
        </article>
        <article class="rounded-2xl border border-border bg-surface p-5">
          <p class="text-xs font-semibold text-muted">Doanh thu ghi nhận</p>
          <p class="mt-2 text-2xl font-bold text-teal-dark tabular-nums">{{ formatVnd(summary.doanhThuGhiNhan) }}</p>
        </article>
        <article class="rounded-2xl border border-border bg-surface p-5">
          <p class="text-xs font-semibold text-muted">Hoàn tiền sự cố</p>
          <p class="mt-2 text-2xl font-bold text-amber-dark tabular-nums">{{ formatVnd(summary.hoanTienSuCo) }}</p>
        </article>
        <article class="rounded-2xl border border-border bg-surface p-5">
          <p class="text-xs font-semibold text-muted">Tổng lượt bán hợp lệ</p>
          <p class="mt-2 text-2xl font-bold text-navy tabular-nums">{{ summary.tongLuotBan }}</p>
        </article>
      </section>

      <p class="rounded-xl border border-border/80 bg-subtle/60 px-4 py-3 text-xs text-slate-600">
        {{ summary.ghiChuPayout }}
      </p>

      <div class="grid gap-6 lg:grid-cols-12">
        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4 lg:col-span-6">
          <div class="flex items-center gap-2">
            <BarChart3 :size="16" class="text-teal" aria-hidden="true" />
            <h2 class="font-display text-base font-bold text-navy">Xu hướng doanh thu theo ngày</h2>
          </div>
          <p v-if="!summary.chuoiDoanhThuTheoNgay.length" class="py-4 text-sm text-muted">
            Chưa có giao dịch bán hàng nào được ghi nhận.
          </p>
          <ul v-else class="space-y-3">
            <li v-for="pt in summary.chuoiDoanhThuTheoNgay" :key="pt.ngay" class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="font-medium text-navy tabular-nums">{{ pt.ngay }}</span>
                <span class="font-semibold text-navy tabular-nums">{{ formatVnd(pt.doanhThuThuan) }}</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-subtle">
                <div
                  class="h-full rounded-full bg-teal"
                  :style="{ width: `${Math.max(4, Math.round((Number(pt.doanhThuThuan) / maxDaily) * 100))}%` }"
                />
              </div>
            </li>
          </ul>
        </section>

        <section class="rounded-2xl border border-border bg-surface p-6 space-y-4 lg:col-span-6">
          <h2 class="font-display text-base font-bold text-navy">Hiệu quả theo khóa học</h2>
          <p v-if="!summary.hieuQuaTheoKhoaHoc.length" class="py-4 text-sm text-muted">
            Chưa có khóa học nào phát sinh lượt mua.
          </p>
          <ul v-else class="divide-y divide-border/70">
            <li
              v-for="c in summary.hieuQuaTheoKhoaHoc"
              :key="c.maKhoaHoc"
              class="flex items-center justify-between gap-3 py-3 text-sm"
            >
              <div class="min-w-0">
                <p class="truncate font-semibold text-navy">{{ c.tieuDe }}</p>
                <p class="text-xs text-muted tabular-nums">{{ c.soLuotBan }} lượt bán</p>
              </div>
              <span class="shrink-0 font-bold text-navy tabular-nums">{{ formatVnd(c.doanhThuThuan) }}</span>
            </li>
          </ul>
        </section>
      </div>

      <!-- Sales History Table -->
      <section class="rounded-2xl border border-border bg-surface p-6 space-y-4">
        <h2 class="font-display text-base font-bold text-navy">Lịch sử bán hàng ({{ items.length }})</h2>
        <UiEmptyState
          v-if="!items.length"
          :icon="ReceiptText"
          title="Chưa có giao dịch bán hàng"
          description="Khi học viên thanh toán thành công khóa học của bạn, giao dịch sẽ hiển thị tại đây."
        />
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-xs sm:text-sm">
            <thead>
              <tr class="border-b border-border text-xs text-muted">
                <th class="pb-2.5 pr-4 font-semibold">Mã đơn</th>
                <th class="pb-2.5 pr-4 font-semibold">Khóa học</th>
                <th class="pb-2.5 pr-4 font-semibold">Giá tại thời điểm mua</th>
                <th class="pb-2.5 pr-4 font-semibold">Trạng thái</th>
                <th class="pb-2.5 font-semibold">Thời gian</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/70">
              <tr v-for="row in items" :key="row.maChiTietDonHang">
                <td class="py-3 pr-4 font-semibold text-navy tabular-nums">{{ row.maSoDonHang }}</td>
                <td class="py-3 pr-4 font-medium text-navy">{{ row.tieuDeSnapshot }}</td>
                <td class="py-3 pr-4 font-bold text-navy tabular-nums">{{ formatVnd(row.giaTaiThoiDiemMua) }}</td>
                <td class="py-3 pr-4 font-semibold text-navy">{{ row.trangThaiDonHang }}</td>
                <td class="py-3 text-muted tabular-nums">{{ formatDateTime(row.ngayThanhToan || row.ngayTao) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>
