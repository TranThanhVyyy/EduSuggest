<script setup>
import { computed, reactive, ref } from 'vue'
import { ArrowLeft, CheckCircle2, Send } from 'lucide-vue-next'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import { getProviderApplication, getUserProfile, submitProviderApplication } from '@/service/userService'

const profile = getUserProfile()
const application = getProviderApplication()
const form = reactive({
  fullName: profile.fullName,
  email: profile.email,
  phone: profile.phone,
  organization: application.organization,
  expertise: application.expertise,
  experience: application.experience,
  introduction: application.introduction,
  reason: application.reason,
})
const errorMessage = ref('')
const toastMessage = ref('')
const waiting = computed(() => application.status === 'pending')

function formatDate(value) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa có dữ liệu' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function submit() {
  try {
    submitProviderApplication(form)
    errorMessage.value = ''
    toastMessage.value = 'Đã lưu hồ sơ gửi thử trong phiên. Hồ sơ chưa được gửi đến Admin hoặc Backend.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể lưu hồ sơ.'
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-5">
    <section class="flex flex-wrap items-end justify-between gap-3">
      <div><p class="text-sm text-muted">Tài khoản User · vai trò hiện tại không thay đổi</p><h1 class="mt-1 text-2xl font-bold text-navy">Trở thành nhà cung cấp khóa học</h1><p class="mt-2 max-w-2xl text-sm leading-6 text-muted">Chia sẻ kiến thức và xây dựng cộng đồng học tập cùng EduSuggest. Đây là hồ sơ bổ sung cho tài khoản User hiện có.</p></div>
      <RouterLink :to="{ name: 'user-profile' }" class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"><ArrowLeft :size="15" aria-hidden="true" /> Hồ sơ cá nhân</RouterLink>
    </section>

    <div class="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(260px,0.7fr)]">
      <form class="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" @submit.prevent="submit">
        <p class="rounded-xl border border-primary/15 bg-primary/5 p-3 text-xs leading-5 text-muted">Thông tin cơ bản được lấy từ hồ sơ mẫu. Chưa có API Provider Application; thao tác gửi chỉ cập nhật trạng thái demo trong bộ nhớ.</p>
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
            <input v-model="form.organization" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted">
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Lĩnh vực chuyên môn *
            <input v-model="form.expertise" required :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted">
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Kinh nghiệm
            <textarea v-model="form.experience" rows="3" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted" placeholder="Mô tả kinh nghiệm liên quan"></textarea>
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Giới thiệu bản thân
            <textarea v-model="form.introduction" rows="3" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"></textarea>
          </label>
          <label class="text-sm font-semibold text-navy sm:col-span-2">Lý do muốn trở thành Provider *
            <textarea v-model="form.reason" required rows="4" :disabled="waiting" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-background disabled:text-muted"></textarea>
          </label>
        </div>
        <p v-if="errorMessage" class="rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
        <button type="submit" :disabled="waiting" class="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"><Send :size="15" aria-hidden="true" /> {{ waiting ? 'Đang chờ xét duyệt' : 'Gửi hồ sơ' }}</button>
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
          <p class="mt-2 text-sm font-semibold text-primary">{{ application.status === 'pending' ? 'Đang chờ xét duyệt' : application.status === 'approved' ? 'Đã được phê duyệt' : application.status === 'rejected' ? 'Bị từ chối' : 'Chưa đăng ký' }}</p>
          <p class="mt-1 text-xs text-muted">Thời gian gửi: {{ formatDate(application.submittedAt) }}</p>
          <p v-if="application.status === 'rejected' && application.rejectionReason" class="mt-3 whitespace-pre-line text-sm text-muted">{{ application.rejectionReason }}</p>
          <p v-else-if="application.status === 'pending'" class="mt-3 text-xs leading-5 text-muted">Trạng thái này chỉ là mẫu trong trình duyệt; hồ sơ chưa tới Admin.</p>
        </article>
      </aside>
    </div>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
