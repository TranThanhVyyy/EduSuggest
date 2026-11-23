<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowRight, Save } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { authState, setCurrentUser } from '@/service/authState'
import { loadCurrentUser } from '@/service/authService'
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
      <p class="mt-2 text-sm leading-6 text-muted">Cập nhật thông tin liên hệ gắn với tài khoản của bạn.</p>
    </header>

    <p v-if="loading" class="py-6 text-sm text-muted" role="status">Đang tải hồ sơ…</p>
    <form v-else class="max-w-2xl space-y-5" @submit.prevent="save">
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
      <UiButton type="submit" :loading="saving"><Save :size="15" aria-hidden="true" /> Lưu thay đổi</UiButton>
    </form>

    <section v-if="!loading" class="border-t border-border pt-6">
      <p class="ui-eyebrow">Nhà cung cấp</p>
      <h2 class="mt-2 text-lg font-medium text-navy">{{ isProvider ? 'Tài khoản nhà cung cấp' : 'Đăng ký trở thành nhà cung cấp' }}</h2>
      <p class="mt-2 text-sm text-muted">{{ isProvider ? 'Bạn có thể quản lý nội dung nhà cung cấp của mình.' : application ? `Trạng thái hồ sơ: ${applicationLabel(applicationStatus)}` : 'Gửi hồ sơ để đề nghị xét duyệt vai trò nhà cung cấp.' }}</p>
      <RouterLink v-if="isProvider" :to="{ name: 'provider-dashboard' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Quản lý khóa học <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      <RouterLink v-else-if="applicationStatus === 'pending'" :to="{ name: 'provider-application' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">Xem hồ sơ đã gửi <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
      <RouterLink v-else :to="{ name: 'provider-application' }" class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-secondary hover:underline">{{ applicationStatus === 'rejected' ? 'Cập nhật hồ sơ' : 'Mở biểu mẫu đăng ký' }} <ArrowRight :size="15" aria-hidden="true" /></RouterLink>
    </section>

    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
