<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, CheckCircle2, Send } from 'lucide-vue-next'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import UiButton from '@/components/ui/UiButton.vue'
import api from '@/service/api'
import { authState } from '@/service/authState'

const profile = authState.user || {}
const application = reactive({
  status: 'not_applied',
  submittedAt: '',
  organization: '',
  expertise: '',
  experience: '',
  introduction: '',
  reason: '',
  rejectionReason: '',
})
const form = reactive({
  fullName: profile.hoTen || '',
  email: profile.email,
  phone: profile.soDienThoai || '',
  organization: '',
  expertise: '',
  experience: '',
  introduction: '',
  reason: '',
})
const errorMessage = ref('')
const toastMessage = ref('')
const loading = ref(true)
const submitting = ref(false)
const waiting = computed(() => application.status === 'pending')

function applyServerApplication(record) {
  const statusMap = { PENDING: 'pending', APPROVED: 'approved', REJECTED: 'rejected' }
  application.status = statusMap[record.trangThai] || 'not_applied'
  application.submittedAt = record.ngayGui || ''
  application.organization = record.toChuc || ''
  application.expertise = record.chuyenMon || ''
  application.experience = record.kinhNghiem || ''
  application.introduction = record.gioiThieu || ''
  application.reason = record.lyDoDangKy || ''
  application.rejectionReason = record.lyDoTuChoi || ''
  Object.assign(form, {
    phone: profile.soDienThoai || '',
    organization: application.organization,
    expertise: application.expertise,
    experience: application.experience,
    introduction: application.introduction,
    reason: application.reason,
  })
}

async function refreshApplication() {
  loading.value = true
  try {
    const { data } = await api.get('/provider/applications/me')
    if (data.length) applyServerApplication(data[0])
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải trạng thái hồ sơ.'
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

async function submit() {
  submitting.value = true
  try {
    const { data } = await api.post('/provider/applications', {
      soDienThoai: form.phone,
      toChuc: form.organization,
      chuyenMon: form.expertise,
      kinhNghiem: form.experience,
      gioiThieu: form.introduction,
      lyDoDangKy: form.reason,
    })
    applyServerApplication(data)
    errorMessage.value = ''
    toastMessage.value = 'Hồ sơ đã được gửi đến Admin để xét duyệt.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể gửi hồ sơ.'
  } finally {
    submitting.value = false
  }
}

onMounted(refreshApplication)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div><p class="text-sm text-muted">Tài khoản User · vai trò hiện tại không thay đổi</p><h1 class="mt-1 text-2xl font-bold text-navy">Trở thành nhà cung cấp khóa học</h1><p class="mt-2 max-w-2xl text-sm leading-6 text-muted">Chia sẻ kiến thức và xây dựng cộng đồng học tập cùng EduSuggest. Đây là hồ sơ bổ sung cho tài khoản User hiện có.</p></div>
      <RouterLink :to="{ name: 'user-profile' }" class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Hồ sơ cá nhân</RouterLink>
    </section>

    <div class="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,0.7fr)]">
      <form class="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" @submit.prevent="submit">
        <p class="rounded-xl border border-primary/15 bg-primary/5 p-3 text-xs leading-5 text-muted">Hồ sơ được lưu trên PostgreSQL. Vai trò tài khoản chỉ thay đổi sau khi Admin chấp nhận.</p>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="text-sm font-semibold text-navy">Họ tên
            <input :value="form.fullName" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm text-muted">
          </label>
          <label class="text-sm font-semibold text-navy">Email
            <input :value="form.email" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm text-muted">
          </label>
          <label class="text-sm font-semibold text-navy">Số điện thoại *
            <input v-model="form.phone" required type="tel" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted">
          </label>
          <label class="text-sm font-semibold text-navy">Tổ chức / đơn vị
            <input v-model="form.organization" required :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted">
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Lĩnh vực chuyên môn *
            <input v-model="form.expertise" required :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted">
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Kinh nghiệm *
            <textarea v-model="form.experience" required rows="3" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted" placeholder="Mô tả kinh nghiệm liên quan"></textarea>
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Giới thiệu bản thân
            <textarea v-model="form.introduction" rows="3" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"></textarea>
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Lý do muốn trở thành Provider *
            <textarea v-model="form.reason" required rows="4" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"></textarea>
          </label>
        </div>
        <p v-if="errorMessage" class="rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
        <UiButton type="submit" :disabled="waiting || loading" :loading="submitting">
          <Send :size="15" aria-hidden="true" /> {{ waiting ? 'Đang chờ xét duyệt' : submitting ? 'Đang gửi...' : 'Gửi hồ sơ' }}
        </UiButton>
      </form>

      <aside class="space-y-4">
        <article class="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 class="font-bold text-navy">Quy trình xét duyệt</h2>
          <ol class="mt-4 space-y-3 text-sm text-muted">
            <li class="flex gap-2"><span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</span>Gửi hồ sơ bổ sung từ tài khoản User.</li>
            <li class="flex gap-2"><span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</span>Admin xem xét thông tin và tài liệu.</li>
            <li class="flex gap-2"><span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">3</span>Backend cấp vai trò Provider nếu được duyệt.</li>
          </ol>
          <p class="mt-4 rounded-xl bg-background p-3 text-xs leading-5 text-muted">Không tạo tài khoản mới. Gửi hồ sơ không tự cấp quyền và không làm thay đổi vai trò hiện tại.</p>
        </article>
        <article class="rounded-2xl border border-accent/20 bg-accent/5 p-5">
          <div class="flex items-center justify-between"><h2 class="font-bold text-navy">Trạng thái hồ sơ</h2><CheckCircle2 :size="19" class="text-accent" aria-hidden="true" /></div>
          <p class="mt-2 text-sm font-semibold text-primary">{{ loading ? 'Đang tải...' : application.status === 'pending' ? 'Đang chờ xét duyệt' : application.status === 'approved' ? 'Đã được phê duyệt' : application.status === 'rejected' ? 'Bị từ chối' : 'Chưa đăng ký' }}</p>
          <p class="mt-1 text-xs text-muted">Thời gian gửi: {{ formatDate(application.submittedAt) }}</p>
          <p v-if="application.status === 'rejected' && application.rejectionReason" class="mt-3 whitespace-pre-line text-sm text-muted">{{ application.rejectionReason }}</p>
          <p v-else-if="application.status === 'pending'" class="mt-3 text-xs leading-5 text-muted">Hồ sơ đã được lưu và đang chờ Admin xử lý.</p>
        </article>
      </aside>
    </div>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
