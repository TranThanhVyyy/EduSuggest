<script setup>
import { onMounted, ref, watch } from 'vue'
import { Check, RefreshCw, X } from 'lucide-vue-next'
import EmptyState from '@/components/reviewer/EmptyState.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiStatusBadge from '@/components/ui/UiStatusBadge.vue'
import api from '@/service/api'

const applications = ref([])
const statusFilter = ref('PENDING')
const rejectionReasons = ref({})
const loading = ref(false)
const busyId = ref(null)
const errorMessage = ref('')
const toastMessage = ref('')

async function loadApplications() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.get('/admin/provider-applications', {
      params: statusFilter.value ? { status: statusFilter.value } : {},
    })
    applications.value = data
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải hồ sơ đăng ký.'
  } finally {
    loading.value = false
  }
}

async function approve(application) {
  busyId.value = application.maDon
  errorMessage.value = ''
  try {
    await api.post(`/admin/provider-applications/${application.maDon}/approve`)
    toastMessage.value = `Đã chấp nhận hồ sơ của ${application.hoTen || application.email}.`
    await loadApplications()
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể chấp nhận hồ sơ.'
  } finally {
    busyId.value = null
  }
}

async function reject(application) {
  const reason = String(rejectionReasons.value[application.maDon] || '').trim()
  if (!reason) {
    errorMessage.value = 'Nhập lý do từ chối trước khi xác nhận.'
    return
  }
  busyId.value = application.maDon
  errorMessage.value = ''
  try {
    await api.post(`/admin/provider-applications/${application.maDon}/reject`, {
      lyDoTuChoi: reason,
    })
    toastMessage.value = `Đã từ chối hồ sơ của ${application.hoTen || application.email}.`
    await loadApplications()
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể từ chối hồ sơ.'
  } finally {
    busyId.value = null
  }
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

watch(statusFilter, loadApplications)
onMounted(loadApplications)
</script>

<template>
  <div class="space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted">Quản lý người dùng</p>
        <h1 class="mt-1 text-2xl font-bold text-navy">Hồ sơ đăng ký nhà cung cấp</h1>
       
      </div>
      <div class="flex items-center gap-2">
        <label for="provider-application-status" class="sr-only">Lọc trạng thái</label>
        <select id="provider-application-status" v-model="statusFilter" class="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm">
          <option value="PENDING">Đang chờ</option>
          <option value="APPROVED">Đã chấp nhận</option>
          <option value="REJECTED">Đã từ chối</option>
          <option value="">Tất cả</option>
        </select>
        <UiButton variant="outline" size="sm" :disabled="loading" @click="loadApplications">
          <RefreshCw :size="15" aria-hidden="true" /> Làm mới
        </UiButton>
      </div>
    </section>

    <p v-if="errorMessage" class="rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
    <p v-if="toastMessage" class="rounded-xl border border-accent/20 bg-accent/5 p-3 text-sm text-navy" role="status">{{ toastMessage }}</p>

    <div v-if="loading && !applications.length" class="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-muted">Đang tải hồ sơ từ Backend...</div>
    <EmptyState v-else-if="!applications.length" title="Không có hồ sơ" description="Không tìm thấy hồ sơ với trạng thái đã chọn." />
    <section v-else class="space-y-4">
      <article v-for="application in applications" :key="application.maDon" class="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <header class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="font-bold text-navy">{{ application.hoTen || 'Chưa có họ tên' }}</h2>
            <p class="mt-1 text-sm text-muted">{{ application.email }} · {{ application.soDienThoai || 'Chưa có số điện thoại' }}</p>
            <p class="mt-1 text-xs text-muted">Gửi lúc {{ formatDate(application.ngayGui) }}</p>
          </div>
          <UiStatusBadge :tone="application.trangThai === 'APPROVED' ? 'success' : application.trangThai === 'REJECTED' ? 'danger' : 'warning'">
            {{ application.trangThai === 'PENDING' ? 'Đang chờ' : application.trangThai === 'APPROVED' ? 'Đã chấp nhận' : 'Đã từ chối' }}
          </UiStatusBadge>
        </header>

        <dl class="grid gap-3 text-sm sm:grid-cols-2">
          <div><dt class="font-semibold text-navy">Tổ chức</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.toChuc }}</dd></div>
          <div><dt class="font-semibold text-navy">Chuyên môn</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.chuyenMon }}</dd></div>
          <div class="sm:col-span-2"><dt class="font-semibold text-navy">Kinh nghiệm</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.kinhNghiem }}</dd></div>
          <div class="sm:col-span-2"><dt class="font-semibold text-navy">Giới thiệu</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.gioiThieu || '—' }}</dd></div>
          <div class="sm:col-span-2"><dt class="font-semibold text-navy">Lý do đăng ký</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.lyDoDangKy }}</dd></div>
          <div v-if="application.lyDoTuChoi" class="sm:col-span-2"><dt class="font-semibold text-navy">Lý do từ chối</dt><dd class="mt-1 whitespace-pre-line text-muted">{{ application.lyDoTuChoi }}</dd></div>
        </dl>

        <div v-if="application.trangThai === 'PENDING'" class="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row">
          <input v-model="rejectionReasons[application.maDon]" class="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm" placeholder="Lý do từ chối (bắt buộc nếu từ chối)">
          <UiButton variant="secondary" size="sm" :disabled="busyId === application.maDon" @click="approve(application)">
            <Check :size="15" aria-hidden="true" /> Chấp nhận
          </UiButton>
          <UiButton variant="danger" size="sm" :disabled="busyId === application.maDon" @click="reject(application)">
            <X :size="15" aria-hidden="true" /> Từ chối
          </UiButton>
        </div>
      </article>
    </section>
  </div>
</template>
