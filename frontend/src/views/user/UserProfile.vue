<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowRight, Eye, EyeOff, KeyRound, Save } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { authState, setCurrentUser } from '@/service/authState'
import { changePassword, loadCurrentUser } from '@/service/authService'
import api from '@/service/api'

const form = reactive({ fullName: '', phone: '' })
const application = ref(null)
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const toastMessage = ref('')
const username = computed(() => authState.user?.tenTaiKhoan || '')
const email = computed(() => authState.user?.email || '')
const isProvider = computed(() => String(authState.user?.tenVaiTro || '').toUpperCase() === 'PROVIDER')

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const passwordSaving = ref(false)
const passwordErrorMessage = ref('')
const passwordSuccessMessage = ref('')

async function loadProfileAndApplication() {
  loading.value = true
  errorMessage.value = ''
  try {
    const user = await loadCurrentUser()
    if (!user) return
    Object.assign(form, { fullName: user.hoTen || '', phone: user.soDienThoai || '' })
    if (!isProvider.value) {
      const { data } = await api.get('/provider/applications/me')
      application.value = data[0] || null
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải hồ sơ. Hãy thử tải lại trang.'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.put('/users/me', {
      hoTen: form.fullName.trim(),
      soDienThoai: form.phone.trim() || null,
    })
    setCurrentUser(data)
    form.fullName = data.hoTen || ''
    form.phone = data.soDienThoai || ''
    toastMessage.value = 'Đã cập nhật hồ sơ.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể cập nhật hồ sơ. Kiểm tra thông tin rồi thử lại.'
  } finally {
    saving.value = false
  }
}

async function handlePasswordChange() {
  passwordErrorMessage.value = ''
  passwordSuccessMessage.value = ''

  if (!passwordForm.currentPassword) {
    passwordErrorMessage.value = 'Vui lòng nhập mật khẩu hiện tại.'
    return
  }
  if (!passwordForm.newPassword) {
    passwordErrorMessage.value = 'Vui lòng nhập mật khẩu mới.'
    return
  }
  if (passwordForm.newPassword.length < 8) {
    passwordErrorMessage.value = 'Mật khẩu mới phải chứa ít nhất 8 ký tự.'
    return
  }
  if (passwordForm.newPassword.length > 128) {
    passwordErrorMessage.value = 'Mật khẩu mới không được vượt quá 128 ký tự.'
    return
  }
  if (passwordForm.newPassword === passwordForm.currentPassword) {
    passwordErrorMessage.value = 'Mật khẩu mới phải khác mật khẩu hiện tại.'
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordErrorMessage.value = 'Mật khẩu xác nhận không trùng khớp.'
    return
  }

  passwordSaving.value = true
  try {
    const res = await changePassword(passwordForm.currentPassword, passwordForm.newPassword)
    passwordSuccessMessage.value = res.message || 'Đổi mật khẩu thành công.'
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    toastMessage.value = 'Đổi mật khẩu thành công.'
  } catch (error) {
    passwordErrorMessage.value = error.response?.data?.detail || 'Không thể đổi mật khẩu. Kiểm tra lại thông tin rồi thử lại.'
  } finally {
    passwordSaving.value = false
  }
}

const applicationStatus = computed(() => application.value?.trangThai?.toLowerCase() || 'not_applied')
function applicationLabel(status) {
  return ({
    not_applied: 'Chưa gửi hồ sơ',
    pending: 'Đang chờ xét duyệt',
    approved: 'Đã được phê duyệt',
    rejected: 'Cần cập nhật hồ sơ',
  })[status] || 'Chưa có trạng thái'
}

onMounted(loadProfileAndApplication)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-8">
    <header class="border-b border-border pb-5">
      <p class="ui-eyebrow">Tài khoản</p>
      <h1 class="ui-page-title mt-2">Hồ sơ cá nhân</h1>
      <p class="mt-2 text-sm leading-6 text-muted">Cập nhật thông tin liên hệ và mật khẩu gắn với tài khoản của bạn.</p>
    </header>

    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải hồ sơ…</p>
    <div v-else class="space-y-8">
      <form class="max-w-2xl space-y-5" @submit.prevent="save">
        <h2 class="text-base font-semibold text-navy">Thông tin liên hệ</h2>
        <div class="grid gap-5 sm:grid-cols-2">
          <label class="text-sm font-medium text-navy">Họ và tên
            <input v-model.trim="form.fullName" required maxlength="255" autocomplete="name" class="ui-input mt-2">
          </label>
          <label class="text-sm font-medium text-navy">Tên tài khoản
            <input :value="username" disabled autocomplete="username" class="ui-input mt-2">
          </label>
          <label class="text-sm font-medium text-navy">Email
            <input :value="email" disabled type="email" autocomplete="email" class="ui-input mt-2">
          </label>
          <label class="text-sm font-medium text-navy">Số điện thoại
            <input v-model.trim="form.phone" type="tel" maxlength="20" autocomplete="tel" class="ui-input mt-2">
          </label>
        </div>
        <p v-if="errorMessage" class="border-l-2 border-danger py-1 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p>
        <UiButton type="submit" :loading="saving"><Save :size="15" aria-hidden="true" /> Lưu thông tin liên hệ</UiButton>
      </form>

      <section class="border-t border-border pt-6">
        <h2 class="text-base font-semibold text-navy">Đổi mật khẩu</h2>
        <p class="mt-1 text-sm text-muted">Mật khẩu mới phải có độ dài từ 8 đến 128 ký tự.</p>
        <form class="mt-4 max-w-2xl space-y-4" @submit.prevent="handlePasswordChange">
          <div class="grid gap-4 sm:grid-cols-1">
            <label class="text-sm font-medium text-navy">Mật khẩu hiện tại
              <div class="relative mt-2">
                <input
                  v-model="passwordForm.currentPassword"
                  :type="showCurrentPassword ? 'text' : 'password'"
                  required
                  maxlength="128"
                  autocomplete="current-password"
                  class="ui-input pr-10"
                  placeholder="Nhập mật khẩu hiện tại"
                >
                <button
                  type="button"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-navy"
                  :aria-label="showCurrentPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                  @click="showCurrentPassword = !showCurrentPassword"
                >
                  <EyeOff v-if="showCurrentPassword" :size="17" aria-hidden="true" />
                  <Eye v-else :size="17" aria-hidden="true" />
                </button>
              </div>
            </label>

            <div class="grid gap-4 sm:grid-cols-2">
              <label class="text-sm font-medium text-navy">Mật khẩu mới
                <div class="relative mt-2">
                  <input
                    v-model="passwordForm.newPassword"
                    :type="showNewPassword ? 'text' : 'password'"
                    required
                    minlength="8"
                    maxlength="128"
                    autocomplete="new-password"
                    class="ui-input pr-10"
                    placeholder="Ít nhất 8 ký tự"
                  >
                  <button
                    type="button"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-navy"
                    :aria-label="showNewPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                    @click="showNewPassword = !showNewPassword"
                  >
                    <EyeOff v-if="showNewPassword" :size="17" aria-hidden="true" />
                    <Eye v-else :size="17" aria-hidden="true" />
                  </button>
                </div>
              </label>

              <label class="text-sm font-medium text-navy">Xác nhận mật khẩu mới
                <div class="relative mt-2">
                  <input
                    v-model="passwordForm.confirmPassword"
                    :type="showConfirmPassword ? 'text' : 'password'"
                    required
                    minlength="8"
                    maxlength="128"
                    autocomplete="new-password"
                    class="ui-input pr-10"
                    placeholder="Nhập lại mật khẩu mới"
                  >
                  <button
                    type="button"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-navy"
                    :aria-label="showConfirmPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                    @click="showConfirmPassword = !showConfirmPassword"
                  >
                    <EyeOff v-if="showConfirmPassword" :size="17" aria-hidden="true" />
                    <Eye v-else :size="17" aria-hidden="true" />
                  </button>
                </div>
              </label>
            </div>
          </div>

          <p v-if="passwordErrorMessage" class="border-l-2 border-danger py-1 pl-3 text-sm text-danger" role="alert">{{ passwordErrorMessage }}</p>
          <p v-if="passwordSuccessMessage" class="border-l-2 border-success py-1 pl-3 text-sm text-success" role="status">{{ passwordSuccessMessage }}</p>

          <UiButton type="submit" :loading="passwordSaving" :disabled="passwordSaving">
            <KeyRound :size="15" aria-hidden="true" /> Đổi mật khẩu
          </UiButton>
        </form>
      </section>

      <section class="border-t border-border pt-6">
        <p class="ui-eyebrow">Nhà cung cấp</p>
        <h2 class="mt-2 text-lg font-medium text-navy">{{ isProvider ? 'Tài khoản nhà cung cấp' : 'Đăng ký trở thành nhà cung cấp' }}</h2>
        <p class="mt-2 text-sm text-muted">{{ isProvider ? 'Bạn có thể quản lý nội dung nhà cung cấp của mình.' : application ? `Trạng thái hồ sơ: ${applicationLabel(applicationStatus)}` : 'Gửi hồ sơ để đề nghị xét duyệt vai trò nhà cung cấp.' }}</p>
        <RouterLink v-if="isProvider" :to="{ name: 'provider-dashboard' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Quản lý khóa học <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
        <RouterLink v-else-if="applicationStatus === 'pending'" :to="{ name: 'provider-application' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Xem hồ sơ đã gửi <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
        <RouterLink v-else :to="{ name: 'provider-application' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">{{ applicationStatus === 'rejected' ? 'Cập nhật hồ sơ' : 'Mở biểu mẫu đăng ký' }} <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      </section>
    </div>

    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
